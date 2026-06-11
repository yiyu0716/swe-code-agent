import json
import os
import subprocess
import sys
from pathlib import Path

from swetrace.training.metrics import load_training_metrics
from swetrace.training.sft_lora import format_messages, run_sft_lora, summarize_train_losses


def _write_messages_dataset(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "manifest.json").write_text(
        json.dumps(
            {
                "version": "sft-mix-test",
                "schema": "messages_v1",
                "counts": {"total_messages": 2},
            }
        )
        + "\n"
    )
    rows = [
        {
            "messages": [
                {"role": "system", "content": "You are a coding agent."},
                {"role": "user", "content": "Fix issue A."},
                {"role": "assistant", "content": "diff --git a/a.py b/a.py\n"},
            ],
            "metadata": {"task_id": "task-a"},
        },
        {
            "messages": [
                {"role": "user", "content": "Fix issue B."},
                {"role": "assistant", "content": "diff --git a/b.py b/b.py\n"},
            ],
            "metadata": {"task_id": "task-b"},
        },
    ]
    (path / "messages.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    )


def test_format_messages_uses_role_blocks_without_tokenizer() -> None:
    text = format_messages(
        {
            "messages": [
                {"role": "user", "content": "Patch this."},
                {"role": "assistant", "content": "done"},
            ]
        }
    )

    assert "USER:\nPatch this." in text
    assert "ASSISTANT:\ndone" in text


def test_run_sft_lora_dry_run_records_training_assets(tmp_path) -> None:
    dataset = tmp_path / "datasets" / "sft_mix_v0.1"
    model = tmp_path / "models" / "qwen"
    out = tmp_path / "training"
    _write_messages_dataset(dataset)
    model.mkdir(parents=True)
    (model / "config.json").write_text('{"model_type": "qwen2"}\n')

    result = run_sft_lora(
        dataset=dataset,
        model=model,
        out=out,
        run_id="sft-lora-test",
        max_steps=2,
        max_train_samples=1,
        dry_run=True,
        git_commit="abc123",
    )

    metrics = load_training_metrics(root=out, run_id="sft-lora-test")
    train_result = json.loads((out / "sft-lora-test" / "train_result.json").read_text())
    snapshot = json.loads((out / "sft-lora-test" / "snapshot.json").read_text())

    assert result["status"] == "dry_run_ok"
    assert result["rows_seen"] == 1
    assert result["formal_training"] is False
    assert snapshot["stage"] == "sft_lora"
    assert snapshot["config"]["dataset_format"] == "messages_v1"
    assert snapshot["config"]["max_steps"] == 2
    assert [row["step"] for row in metrics] == [1, 2]
    assert metrics[-1]["mode"] == "dry_run_no_weight_update"
    assert train_result["status"] == "dry_run_ok"
    assert train_result["outputs"]["adapter"] == str(out / "sft-lora-test" / "adapter")


def test_run_sft_lora_rejects_empty_messages_dataset(tmp_path) -> None:
    dataset = tmp_path / "datasets" / "sft_mix_v0.1"
    model = tmp_path / "models" / "qwen"
    dataset.mkdir(parents=True)
    model.mkdir(parents=True)
    (dataset / "messages.jsonl").write_text("")

    try:
        run_sft_lora(
            dataset=dataset,
            model=model,
            out=tmp_path / "training",
            run_id="bad",
            dry_run=True,
        )
    except ValueError as exc:
        assert "messages.jsonl is empty" in str(exc)
    else:
        raise AssertionError("expected empty messages dataset to fail")


def test_run_sft_lora_script_supports_dry_run_cli(tmp_path) -> None:
    dataset = tmp_path / "datasets" / "sft_mix_v0.1"
    model = tmp_path / "models" / "qwen"
    out = tmp_path / "training"
    _write_messages_dataset(dataset)
    model.mkdir(parents=True)
    (model / "config.json").write_text('{"model_type": "qwen2"}\n')

    env = {
        **os.environ,
        "SWETRACE_PYTHON": sys.executable,
        "SWETRACE_SFT_DATASET": str(dataset),
        "SWETRACE_MODEL": str(model),
        "SWETRACE_TRAIN_OUT": str(out),
        "SWETRACE_TRAIN_RUN_ID": "script-dry",
        "SWETRACE_DRY_RUN": "1",
        "SWETRACE_MAX_STEPS": "1",
        "SWETRACE_MAX_TRAIN_SAMPLES": "1",
    }

    completed = subprocess.run(
        ["bash", "scripts/run_sft_lora.sh"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "dry_run_ok"
    assert (out / "script-dry" / "train_result.json").exists()


def test_summarize_train_losses_separates_aggregate_and_last_logged_loss() -> None:
    summary = summarize_train_losses(
        log_history=[
            {"loss": 1.2},
            {"loss": 0.1},
            {"train_loss": 0.4},
        ],
        train_metrics={"train_loss": 0.42},
    )

    assert summary["train_loss"] == 0.42
    assert summary["last_logged_loss"] == 0.1
