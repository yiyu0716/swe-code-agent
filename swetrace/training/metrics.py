import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from swetrace.training.snapshot import DEFAULT_TRAINING_OUT


def append_metric(
    *,
    root: Path = DEFAULT_TRAINING_OUT,
    run_id: str,
    metric: dict[str, Any],
) -> dict[str, Any]:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    row = {"created_at": datetime.now(UTC).isoformat(), **metric}
    path = run_dir / "metrics.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def load_training_metrics(
    *,
    root: Path = DEFAULT_TRAINING_OUT,
    run_id: str,
) -> list[dict[str, Any]]:
    path = root / run_id / "metrics.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def list_training_runs(root: Path = DEFAULT_TRAINING_OUT) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    runs = []
    for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        snapshot = _read_optional_json(run_dir / "snapshot.json")
        metrics = load_training_metrics(root=root, run_id=run_dir.name)
        runs.append(
            {
                "run_id": run_dir.name,
                "path": str(run_dir),
                "snapshot": snapshot,
                "latest_metric": metrics[-1] if metrics else None,
                "num_metrics": len(metrics),
            }
        )
    return runs


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())
