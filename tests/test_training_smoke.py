import json
from pathlib import Path

from swetrace.training.metrics import load_training_metrics
from swetrace.training.smoke import run_dpo_smoke, run_sft_smoke


def test_run_sft_smoke_validates_rows_and_writes_metrics(tmp_path) -> None:
    dataset = tmp_path / "datasets" / "v0.2"
    dataset.mkdir(parents=True)
    (dataset / "manifest.json").write_text(
        json.dumps({"version": "v0.2-test", "counts": {"sft_patch": 1}})
    )
    (dataset / "sft_patch.jsonl").write_text(
        json.dumps(
            {
                "type": "sft_patch",
                "instruction": "Produce a patch.",
                "input": "Issue:\nFix it.",
                "output": "diff --git a/a.py b/a.py\n",
                "meta": {"task_id": "task-1", "official_resolved": True},
            }
        )
        + "\n"
    )
    model = tmp_path / "model"
    model.mkdir()
    out = tmp_path / "training"

    result = run_sft_smoke(
        dataset=dataset,
        model=model,
        out=out,
        run_id="sft-smoke",
        max_steps=2,
        load_tokenizer=False,
        git_commit="abc123",
    )

    metrics = load_training_metrics(root=out, run_id="sft-smoke")
    assert result["status"] == "dry_run_ok"
    assert result["rows_seen"] == 1
    assert result["steps"] == 2
    assert result["snapshot"]["stage"] == "sft_smoke"
    assert [row["step"] for row in metrics] == [1, 2]
    assert metrics[-1]["train_loss"] > 0


def test_run_dpo_smoke_validates_pairs_and_writes_metrics(tmp_path) -> None:
    dataset = tmp_path / "datasets" / "v0.2"
    dataset.mkdir(parents=True)
    (dataset / "manifest.json").write_text(
        json.dumps({"version": "v0.2-test", "counts": {"dpo_main": 1}})
    )
    (dataset / "dpo_main.jsonl").write_text(
        json.dumps(
            {
                "type": "dpo_pair",
                "prompt": "Issue:\nFix it.",
                "chosen": "good patch",
                "rejected": "bad patch",
                "meta": {"task_id": "task-1", "official_resolved": False},
            }
        )
        + "\n"
    )
    model = tmp_path / "model"
    model.mkdir()
    out = tmp_path / "training"

    result = run_dpo_smoke(
        dataset=dataset,
        model=model,
        out=out,
        run_id="dpo-smoke",
        max_steps=2,
        load_tokenizer=False,
        git_commit="abc123",
    )

    metrics = load_training_metrics(root=out, run_id="dpo-smoke")
    assert result["status"] == "dry_run_ok"
    assert result["rows_seen"] == 1
    assert result["steps"] == 2
    assert result["snapshot"]["stage"] == "dpo_smoke"
    assert metrics[0]["stage"] == "dpo_smoke"
    assert metrics[-1]["train_loss"] > 0
