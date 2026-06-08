import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_TRAINING_OUT = Path("/data/yiyuldx/swe/outputs/training")


def create_training_snapshot(
    *,
    out: Path = DEFAULT_TRAINING_OUT,
    run_id: str,
    stage: str,
    dataset: Path,
    model: Path,
    git_commit: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    run_dir = out / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    dataset_manifest = _read_optional_json(dataset / "manifest.json")
    snapshot = {
        "run_id": run_id,
        "stage": stage,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "path": str(dataset),
            "version": dataset_manifest.get("version"),
            "counts": dataset_manifest.get("counts", {}),
        },
        "model": {
            "path": str(model),
            "config_exists": (model / "config.json").exists(),
        },
        "git_commit": git_commit,
        "config": config,
        "outputs": {
            "run_dir": str(run_dir),
            "metrics": str(run_dir / "metrics.jsonl"),
            "snapshot": str(run_dir / "snapshot.json"),
        },
    }
    (run_dir / "snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    )
    return snapshot


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())
