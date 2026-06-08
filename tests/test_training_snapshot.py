import json
from pathlib import Path

from swetrace.training.metrics import append_metric, list_training_runs, load_training_metrics
from swetrace.training.snapshot import create_training_snapshot


def test_create_training_snapshot_records_inputs_and_dataset_counts(tmp_path) -> None:
    dataset = tmp_path / "datasets" / "v0.2"
    dataset.mkdir(parents=True)
    (dataset / "manifest.json").write_text(
        json.dumps(
            {
                "version": "v0.2-test",
                "counts": {
                    "sft_patch": 2,
                    "dpo_main": 3,
                    "reward_logs": 4,
                    "train_ready": True,
                },
            }
        )
    )
    model = tmp_path / "models" / "qwen"
    model.mkdir(parents=True)
    (model / "config.json").write_text('{"model_type": "qwen2"}')
    out = tmp_path / "training"

    snapshot = create_training_snapshot(
        out=out,
        run_id="sft-smoke-test",
        stage="sft_smoke",
        dataset=dataset,
        model=model,
        git_commit="abc123",
        config={"max_steps": 3, "learning_rate": 1e-4},
    )

    manifest_path = out / "sft-smoke-test" / "snapshot.json"
    assert snapshot["run_id"] == "sft-smoke-test"
    assert snapshot["stage"] == "sft_smoke"
    assert snapshot["dataset"]["version"] == "v0.2-test"
    assert snapshot["dataset"]["counts"]["sft_patch"] == 2
    assert snapshot["model"]["path"] == str(model)
    assert snapshot["git_commit"] == "abc123"
    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text()) == snapshot


def test_metrics_append_read_and_list_runs(tmp_path) -> None:
    root = tmp_path / "training"

    append_metric(
        root=root,
        run_id="run-b",
        metric={
            "stage": "sft_smoke",
            "step": 1,
            "train_loss": 1.25,
            "learning_rate": 2e-4,
        },
    )
    append_metric(
        root=root,
        run_id="run-b",
        metric={"stage": "sft_smoke", "step": 2, "train_loss": 1.0},
    )
    create_training_snapshot(
        out=root,
        run_id="run-a",
        stage="dpo_smoke",
        dataset=tmp_path / "missing-dataset",
        model=tmp_path / "missing-model",
        git_commit="abc123",
        config={},
    )

    metrics = load_training_metrics(root=root, run_id="run-b")
    runs = list_training_runs(root=root)

    assert [row["step"] for row in metrics] == [1, 2]
    assert metrics[0]["train_loss"] == 1.25
    assert runs[0]["run_id"] == "run-a"
    assert runs[1]["run_id"] == "run-b"
    assert runs[1]["latest_metric"]["step"] == 2
