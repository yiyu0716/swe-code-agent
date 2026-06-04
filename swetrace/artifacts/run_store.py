import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from swetrace.schema import RunReport, TaskSpec, TrajectoryStep


class RunStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create_run(self, task: TaskSpec, agent: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_task_id = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in task.task_id)
        run_id = f"{timestamp}-{safe_task_id}-{agent}-{uuid4().hex[:8]}"
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        self.write_json(run_id, "task.json", task.model_dump(mode="json"))
        return run_id

    def run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def write_json(self, run_id: str, filename: str, payload: dict) -> Path:
        path = self.run_dir(run_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return path

    def write_text(self, run_id: str, filename: str, content: str) -> Path:
        path = self.run_dir(run_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def write_trajectory(self, run_id: str, steps: list[TrajectoryStep]) -> Path:
        path = self.run_dir(run_id) / "trajectory.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as fh:
            for step in steps:
                fh.write(step.model_dump_json() + "\n")
        return path

    def write_report(self, report: RunReport) -> Path:
        return self.write_json(report.run_id, "report.json", report.model_dump(mode="json"))
