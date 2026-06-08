import json
import subprocess
from itertools import islice
from pathlib import Path
from typing import Any

import typer

from swetrace.training.metrics import append_metric
from swetrace.training.snapshot import DEFAULT_TRAINING_OUT, create_training_snapshot

DEFAULT_DATASET = Path("/data/yiyuldx/swe/outputs/datasets/v0.2")
DEFAULT_MODEL = Path("/data/yiyuldx/swe/models/Qwen2.5-Coder-7B-Instruct")

app = typer.Typer(add_completion=False)


def run_sft_smoke(
    *,
    dataset: Path = DEFAULT_DATASET,
    model: Path = DEFAULT_MODEL,
    out: Path = DEFAULT_TRAINING_OUT,
    run_id: str,
    max_steps: int = 3,
    load_tokenizer: bool = True,
    git_commit: str | None = None,
) -> dict[str, Any]:
    rows = _read_jsonl(dataset / "sft_patch.jsonl")
    _validate_sft_rows(rows)
    tokenizer_info = _tokenizer_info(model, rows, _format_sft, load_tokenizer=load_tokenizer)
    snapshot = create_training_snapshot(
        out=out,
        run_id=run_id,
        stage="sft_smoke",
        dataset=dataset,
        model=model,
        git_commit=git_commit or _git_commit(),
        config={
            "max_steps": max_steps,
            "load_tokenizer": load_tokenizer,
            "tokenizer": tokenizer_info,
            "mode": "dry_run_no_weight_update",
        },
    )
    _write_smoke_metrics(
        out=out,
        run_id=run_id,
        stage="sft_smoke",
        max_steps=max_steps,
        base_loss=1.0 + min(len(rows), 100) / 1000,
    )
    return {
        "status": "dry_run_ok",
        "stage": "sft_smoke",
        "run_id": run_id,
        "rows_seen": len(rows),
        "steps": max_steps,
        "snapshot": snapshot,
    }


def run_dpo_smoke(
    *,
    dataset: Path = DEFAULT_DATASET,
    model: Path = DEFAULT_MODEL,
    out: Path = DEFAULT_TRAINING_OUT,
    run_id: str,
    max_steps: int = 3,
    load_tokenizer: bool = True,
    git_commit: str | None = None,
) -> dict[str, Any]:
    rows = _read_jsonl(dataset / "dpo_main.jsonl")
    _validate_dpo_rows(rows)
    tokenizer_info = _tokenizer_info(model, rows, _format_dpo, load_tokenizer=load_tokenizer)
    snapshot = create_training_snapshot(
        out=out,
        run_id=run_id,
        stage="dpo_smoke",
        dataset=dataset,
        model=model,
        git_commit=git_commit or _git_commit(),
        config={
            "max_steps": max_steps,
            "load_tokenizer": load_tokenizer,
            "tokenizer": tokenizer_info,
            "mode": "dry_run_no_weight_update",
        },
    )
    _write_smoke_metrics(
        out=out,
        run_id=run_id,
        stage="dpo_smoke",
        max_steps=max_steps,
        base_loss=0.7 + min(len(rows), 100) / 1000,
    )
    return {
        "status": "dry_run_ok",
        "stage": "dpo_smoke",
        "run_id": run_id,
        "rows_seen": len(rows),
        "steps": max_steps,
        "snapshot": snapshot,
    }


@app.command("sft")
def sft_command(
    dataset: Path = typer.Option(DEFAULT_DATASET, exists=True, file_okay=False),
    model: Path = typer.Option(DEFAULT_MODEL, exists=True, file_okay=False),
    out: Path = typer.Option(DEFAULT_TRAINING_OUT),
    run_id: str = typer.Option("sft-smoke"),
    max_steps: int = typer.Option(3, min=1),
    load_tokenizer: bool = typer.Option(True, "--load-tokenizer/--no-load-tokenizer"),
) -> None:
    typer.echo(
        json.dumps(
            run_sft_smoke(
                dataset=dataset,
                model=model,
                out=out,
                run_id=run_id,
                max_steps=max_steps,
                load_tokenizer=load_tokenizer,
            ),
            ensure_ascii=False,
        )
    )


@app.command("dpo")
def dpo_command(
    dataset: Path = typer.Option(DEFAULT_DATASET, exists=True, file_okay=False),
    model: Path = typer.Option(DEFAULT_MODEL, exists=True, file_okay=False),
    out: Path = typer.Option(DEFAULT_TRAINING_OUT),
    run_id: str = typer.Option("dpo-smoke"),
    max_steps: int = typer.Option(3, min=1),
    load_tokenizer: bool = typer.Option(True, "--load-tokenizer/--no-load-tokenizer"),
) -> None:
    typer.echo(
        json.dumps(
            run_dpo_smoke(
                dataset=dataset,
                model=model,
                out=out,
                run_id=run_id,
                max_steps=max_steps,
                load_tokenizer=load_tokenizer,
            ),
            ensure_ascii=False,
        )
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _validate_sft_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("sft_patch.jsonl is empty")
    bad = [
        row.get("task_id") or row.get("meta", {}).get("task_id") or "<missing-task>"
        for row in rows
        if not (
            row.get("type") == "sft_patch"
            and str(row.get("instruction") or "").strip()
            and str(row.get("input") or "").strip()
            and str(row.get("output") or "").strip()
        )
    ]
    if bad:
        raise ValueError(f"invalid SFT rows: {bad[:5]}")


def _validate_dpo_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("dpo_main.jsonl is empty")
    bad = [
        row.get("meta", {}).get("task_id") or "<missing-task>"
        for row in rows
        if not (
            row.get("type") == "dpo_pair"
            and str(row.get("prompt") or "").strip()
            and str(row.get("chosen") or "").strip()
            and str(row.get("rejected") or "").strip()
            and row.get("chosen") != row.get("rejected")
        )
    ]
    if bad:
        raise ValueError(f"invalid DPO rows: {bad[:5]}")


def _tokenizer_info(
    model: Path,
    rows: list[dict[str, Any]],
    formatter,
    *,
    load_tokenizer: bool,
) -> dict[str, Any]:
    if not load_tokenizer:
        return {"loaded": False}
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model), trust_remote_code=True, local_files_only=True)
    samples = [formatter(row) for row in islice(rows, 0, min(2, len(rows)))]
    token_counts = [len(tokenizer(sample, add_special_tokens=False)["input_ids"]) for sample in samples]
    return {
        "loaded": True,
        "class": tokenizer.__class__.__name__,
        "sample_token_counts": token_counts,
    }


def _format_sft(row: dict[str, Any]) -> str:
    return (
        f"{row['instruction']}\n\n"
        f"{row['input']}\n\n"
        f"Patch:\n{row['output']}"
    )


def _format_dpo(row: dict[str, Any]) -> str:
    return (
        f"{row['prompt']}\n\n"
        f"Chosen patch:\n{row['chosen']}\n\n"
        f"Rejected patch:\n{row['rejected']}"
    )


def _write_smoke_metrics(
    *,
    out: Path,
    run_id: str,
    stage: str,
    max_steps: int,
    base_loss: float,
) -> None:
    for step in range(1, max_steps + 1):
        append_metric(
            root=out,
            run_id=run_id,
            metric={
                "stage": stage,
                "step": step,
                "train_loss": round(base_loss / step, 6),
                "eval_loss": round((base_loss + 0.1) / step, 6),
                "learning_rate": 0.0002,
                "mode": "dry_run_no_weight_update",
            },
        )


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


if __name__ == "__main__":
    app()
