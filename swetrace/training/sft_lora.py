import json
import os
import random
import subprocess
from itertools import islice
from pathlib import Path
from typing import Any

import typer

from swetrace.training.metrics import append_metric
from swetrace.training.snapshot import DEFAULT_TRAINING_OUT, create_training_snapshot

DEFAULT_DATASET = Path("/data/yiyuldx/swe/outputs/datasets/sft_mix_v0.1")
DEFAULT_MODEL = Path("/data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct")
DEFAULT_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]

app = typer.Typer(add_completion=False)


def run_sft_lora(
    *,
    dataset: Path = DEFAULT_DATASET,
    model: Path = DEFAULT_MODEL,
    out: Path = DEFAULT_TRAINING_OUT,
    run_id: str,
    max_steps: int = 50,
    max_train_samples: int | None = None,
    max_seq_length: int = 1024,
    learning_rate: float = 2e-4,
    per_device_train_batch_size: int = 1,
    gradient_accumulation_steps: int = 8,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    target_modules: list[str] | None = None,
    use_4bit: bool = True,
    bf16: bool = True,
    seed: int = 42,
    logging_steps: int = 1,
    dry_run: bool = False,
    git_commit: str | None = None,
) -> dict[str, Any]:
    rows = _load_messages_rows(dataset)
    if max_train_samples is not None:
        rows = list(islice(rows, 0, max_train_samples))
    _validate_messages_rows(rows)
    target_modules = target_modules or DEFAULT_TARGET_MODULES
    run_dir = out / run_id
    adapter_dir = run_dir / "adapter"

    config = {
        "dataset_format": "messages_v1",
        "max_steps": max_steps,
        "max_train_samples": max_train_samples,
        "max_seq_length": max_seq_length,
        "learning_rate": learning_rate,
        "per_device_train_batch_size": per_device_train_batch_size,
        "gradient_accumulation_steps": gradient_accumulation_steps,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "lora_dropout": lora_dropout,
        "target_modules": target_modules,
        "use_4bit": use_4bit,
        "bf16": bf16,
        "seed": seed,
        "logging_steps": logging_steps,
        "mode": "dry_run_no_weight_update" if dry_run else "formal_sft_lora",
        "formal_training": not dry_run,
    }
    snapshot = create_training_snapshot(
        out=out,
        run_id=run_id,
        stage="sft_lora",
        dataset=dataset,
        model=model,
        git_commit=git_commit or _git_commit(),
        config=config,
    )
    if dry_run:
        result = _run_dry_sft(
            out=out,
            run_id=run_id,
            rows=rows,
            max_steps=max_steps,
            adapter_dir=adapter_dir,
            snapshot=snapshot,
        )
    else:
        result = _run_real_sft(
            dataset=dataset,
            model=model,
            out=out,
            run_id=run_id,
            run_dir=run_dir,
            adapter_dir=adapter_dir,
            rows=rows,
            config=config,
        )
    (run_dir / "train_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    return result


def format_messages(row: dict[str, Any], tokenizer: Any | None = None) -> str:
    messages = row["messages"]
    if tokenizer is not None and getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    parts = []
    for message in messages:
        parts.append(f"{message['role'].upper()}:\n{message['content']}")
    return "\n\n".join(parts)


def _run_dry_sft(
    *,
    out: Path,
    run_id: str,
    rows: list[dict[str, Any]],
    max_steps: int,
    adapter_dir: Path,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    base_loss = 1.2 + min(len(rows), 100) / 1000
    for step in range(1, max_steps + 1):
        append_metric(
            root=out,
            run_id=run_id,
            metric={
                "stage": "sft_lora",
                "step": step,
                "train_loss": round(base_loss / step, 6),
                "learning_rate": 2e-4,
                "mode": "dry_run_no_weight_update",
            },
        )
    return {
        "status": "dry_run_ok",
        "stage": "sft_lora",
        "run_id": run_id,
        "rows_seen": len(rows),
        "steps": max_steps,
        "formal_training": False,
        "snapshot": snapshot,
        "outputs": {
            "adapter": str(adapter_dir),
            "metrics": str(out / run_id / "metrics.jsonl"),
            "train_result": str(out / run_id / "train_result.json"),
        },
    }


def _run_real_sft(
    *,
    dataset: Path,
    model: Path,
    out: Path,
    run_id: str,
    run_dir: Path,
    adapter_dir: Path,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    _disable_non_torch_backends()
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainerCallback,
        TrainingArguments,
        set_seed,
    )

    set_seed(int(config["seed"]))
    random.seed(int(config["seed"]))
    tokenizer = AutoTokenizer.from_pretrained(
        str(model),
        trust_remote_code=True,
        local_files_only=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    texts = [format_messages(row, tokenizer=tokenizer) for row in rows]
    train_dataset = _TokenizedTextDataset(
        texts=texts,
        tokenizer=tokenizer,
        max_seq_length=int(config["max_seq_length"]),
    )

    quantization_config = None
    if bool(config["use_4bit"]):
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    model_kwargs = {
        "trust_remote_code": True,
        "local_files_only": True,
        "torch_dtype": torch.bfloat16 if bool(config["bf16"]) else torch.float16,
        "device_map": {"": 0},
    }
    if quantization_config is not None:
        model_kwargs["quantization_config"] = quantization_config
    base_model = AutoModelForCausalLM.from_pretrained(str(model), **model_kwargs)
    base_model.config.use_cache = False
    if hasattr(base_model, "gradient_checkpointing_enable"):
        base_model.gradient_checkpointing_enable()
    if quantization_config is not None:
        base_model = prepare_model_for_kbit_training(base_model)

    lora_config = LoraConfig(
        r=int(config["lora_r"]),
        lora_alpha=int(config["lora_alpha"]),
        lora_dropout=float(config["lora_dropout"]),
        target_modules=list(config["target_modules"]),
        bias="none",
        task_type="CAUSAL_LM",
    )
    peft_model = get_peft_model(base_model, lora_config)
    trainable_params, total_params = _count_parameters(peft_model)

    training_args = TrainingArguments(
        output_dir=str(run_dir / "checkpoints"),
        per_device_train_batch_size=int(config["per_device_train_batch_size"]),
        gradient_accumulation_steps=int(config["gradient_accumulation_steps"]),
        max_steps=int(config["max_steps"]),
        learning_rate=float(config["learning_rate"]),
        bf16=bool(config["bf16"]),
        logging_steps=int(config["logging_steps"]),
        save_strategy="no",
        report_to=[],
        remove_unused_columns=False,
        optim="paged_adamw_8bit" if bool(config["use_4bit"]) else "adamw_torch",
        gradient_checkpointing=True,
    )
    trainer = Trainer(
        model=peft_model,
        args=training_args,
        train_dataset=train_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        callbacks=[_metrics_callback_class(TrainerCallback)(root=out, run_id=run_id)],
    )
    train_output = trainer.train()
    adapter_dir.mkdir(parents=True, exist_ok=True)
    peft_model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(run_dir / "tokenizer"))

    loss_summary = summarize_train_losses(
        log_history=trainer.state.log_history,
        train_metrics=train_output.metrics,
    )
    return {
        "status": "formal_sft_lora_ok",
        "stage": "sft_lora",
        "run_id": run_id,
        "rows_seen": len(rows),
        "steps": int(train_output.global_step),
        "formal_training": True,
        "dataset": str(dataset),
        "model": str(model),
        "train_loss": loss_summary["train_loss"],
        "last_logged_loss": loss_summary["last_logged_loss"],
        "train_runtime": float(train_output.metrics.get("train_runtime", 0.0)),
        "train_samples_per_second": float(
            train_output.metrics.get("train_samples_per_second", 0.0)
        ),
        "trainable_params": trainable_params,
        "total_params": total_params,
        "outputs": {
            "adapter": str(adapter_dir),
            "tokenizer": str(run_dir / "tokenizer"),
            "metrics": str(run_dir / "metrics.jsonl"),
            "train_result": str(run_dir / "train_result.json"),
        },
    }


def summarize_train_losses(
    *,
    log_history: list[dict[str, Any]],
    train_metrics: dict[str, Any],
) -> dict[str, float | None]:
    last_logged_loss = None
    for row in reversed(log_history):
        if "loss" in row:
            last_logged_loss = float(row["loss"])
            break
    train_loss = train_metrics.get("train_loss")
    return {
        "train_loss": float(train_loss) if train_loss is not None else last_logged_loss,
        "last_logged_loss": last_logged_loss,
    }


class _TokenizedTextDataset:
    def __init__(
        self,
        *,
        texts: list[str],
        tokenizer: Any,
        max_seq_length: int,
    ) -> None:
        self.items = [
            tokenizer(
                text,
                truncation=True,
                max_length=max_seq_length,
                add_special_tokens=True,
            )
            for text in texts
        ]

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> dict[str, list[int]]:
        return self.items[index]


def _metrics_callback_class(trainer_callback_cls: type) -> type:
    class MetricsCallback(trainer_callback_cls):
        def __init__(self, *, root: Path, run_id: str) -> None:
            self.root = root
            self.run_id = run_id

        def on_log(self, args, state, control, logs=None, **kwargs):  # noqa: ANN001, ANN003
            logs = logs or {}
            metric: dict[str, Any] = {
                "stage": "sft_lora",
                "step": int(state.global_step),
                "mode": "formal_sft_lora",
            }
            if "loss" in logs:
                metric["train_loss"] = float(logs["loss"])
            if "learning_rate" in logs:
                metric["learning_rate"] = float(logs["learning_rate"])
            if "grad_norm" in logs:
                metric["grad_norm"] = float(logs["grad_norm"])
            if "epoch" in logs:
                metric["epoch"] = float(logs["epoch"])
            if any(key in metric for key in ("train_loss", "learning_rate", "grad_norm")):
                append_metric(root=self.root, run_id=self.run_id, metric=metric)

    return MetricsCallback


def _load_messages_rows(dataset: Path) -> list[dict[str, Any]]:
    return _read_jsonl(dataset / "messages.jsonl")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _validate_messages_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("messages.jsonl is empty")
    bad = []
    for index, row in enumerate(rows):
        messages = row.get("messages")
        if not isinstance(messages, list) or not messages:
            bad.append(index)
            continue
        if not any(isinstance(message, dict) and message.get("role") == "assistant" for message in messages):
            bad.append(index)
            continue
        for message in messages:
            if not (
                isinstance(message, dict)
                and str(message.get("role") or "").strip()
                and str(message.get("content") or "").strip()
            ):
                bad.append(index)
                break
    if bad:
        raise ValueError(f"invalid messages rows: {bad[:5]}")


def _disable_non_torch_backends() -> None:
    os.environ.setdefault("USE_TF", "0")
    os.environ.setdefault("USE_FLAX", "0")
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")


def _count_parameters(model: Any) -> tuple[int, int]:
    trainable = 0
    total = 0
    for parameter in model.parameters():
        count = parameter.numel()
        total += count
        if parameter.requires_grad:
            trainable += count
    return trainable, total


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip()


@app.command("sft-lora")
def sft_lora_command(
    dataset: Path = typer.Option(DEFAULT_DATASET, exists=True, file_okay=False),
    model: Path = typer.Option(DEFAULT_MODEL, exists=True, file_okay=False),
    out: Path = typer.Option(DEFAULT_TRAINING_OUT),
    run_id: str = typer.Option("sft-lora"),
    max_steps: int = typer.Option(50, min=1),
    max_train_samples: int | None = typer.Option(None, min=1),
    max_seq_length: int = typer.Option(1024, min=128),
    learning_rate: float = typer.Option(2e-4),
    per_device_train_batch_size: int = typer.Option(1, min=1),
    gradient_accumulation_steps: int = typer.Option(8, min=1),
    lora_r: int = typer.Option(16, min=1),
    lora_alpha: int = typer.Option(32, min=1),
    lora_dropout: float = typer.Option(0.05, min=0.0),
    use_4bit: bool = typer.Option(True, "--use-4bit/--no-4bit"),
    bf16: bool = typer.Option(True, "--bf16/--no-bf16"),
    dry_run: bool = typer.Option(False, "--dry-run"),
) -> None:
    typer.echo(
        json.dumps(
            run_sft_lora(
                dataset=dataset,
                model=model,
                out=out,
                run_id=run_id,
                max_steps=max_steps,
                max_train_samples=max_train_samples,
                max_seq_length=max_seq_length,
                learning_rate=learning_rate,
                per_device_train_batch_size=per_device_train_batch_size,
                gradient_accumulation_steps=gradient_accumulation_steps,
                lora_r=lora_r,
                lora_alpha=lora_alpha,
                lora_dropout=lora_dropout,
                use_4bit=use_4bit,
                bf16=bf16,
                dry_run=dry_run,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    app()
