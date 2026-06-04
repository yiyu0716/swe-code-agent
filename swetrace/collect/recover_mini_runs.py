import json
from pathlib import Path

import typer

from swetrace.adapters.mini_swe_agent import find_trajectory_file, parse_mini_trajectory
from swetrace.artifacts import RunStore
from swetrace.schema import TaskSpec

app = typer.Typer(add_completion=False)


@app.command()
def main(
    runs: Path = typer.Option(Path("runs"), exists=True, file_okay=False, help="Run artifact root."),
    overwrite: bool = typer.Option(False, help="Rewrite existing normalized reports."),
) -> None:
    store = RunStore(runs)
    recovered = 0
    skipped = 0
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        if not overwrite and (run_dir / "report.json").exists():
            skipped += 1
            continue
        task_path = run_dir / "task.json"
        raw_dir = run_dir / "raw_mini_swe_agent"
        if not task_path.exists() or not raw_dir.exists():
            skipped += 1
            continue
        task = TaskSpec.model_validate_json(task_path.read_text())
        trajectory_path = find_trajectory_file(raw_dir, task.task_id)
        if trajectory_path is None:
            skipped += 1
            continue

        payload = json.loads(trajectory_path.read_text())
        parsed = parse_mini_trajectory(
            payload=payload,
            run_id=run_dir.name,
            task_id=task.task_id,
            agent="mini-swe-agent",
        )
        store.write_trajectory(run_dir.name, parsed.steps)
        store.write_text(run_dir.name, "patch.diff", parsed.patch)
        store.write_text(run_dir.name, "test.log", parsed.test_log)
        store.write_report(parsed.report)
        if not (run_dir / "raw_agent.log").exists():
            store.write_text(run_dir.name, "raw_agent.log", "")
        recovered += 1

    typer.echo(json.dumps({"recovered_runs": recovered, "skipped_runs": skipped}, ensure_ascii=False))


if __name__ == "__main__":
    app()
