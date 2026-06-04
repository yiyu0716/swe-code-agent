import json
from pathlib import Path

import typer

from swetrace.data_builder.build_reward_logs import build_reward_logs
from swetrace.data_builder.build_sft import build_sft_debug, build_sft_patch, build_sft_plan
from swetrace.schema import RunReport, TaskSpec, TrajectoryStep

app = typer.Typer(add_completion=False)


def load_run(run_dir: Path) -> tuple[TaskSpec, list[TrajectoryStep], str, str, RunReport]:
    task = TaskSpec.model_validate_json((run_dir / "task.json").read_text())
    steps = [
        TrajectoryStep.model_validate_json(line)
        for line in (run_dir / "trajectory.jsonl").read_text().splitlines()
        if line.strip()
    ]
    patch = _read_optional(run_dir / "patch.diff")
    test_log = _read_optional(run_dir / "test.log")
    report = RunReport.model_validate_json((run_dir / "report.json").read_text())
    return task, steps, patch, test_log, report


def _read_optional(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text()


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


@app.command()
def main(
    runs: Path = typer.Option(..., exists=True, file_okay=False, help="Run artifact root."),
    out: Path = typer.Option(Path("outputs/datasets"), help="Dataset output directory."),
) -> None:
    sft_plan = []
    sft_patch = []
    sft_debug = []
    reward_logs = []

    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        required = [run_dir / "task.json", run_dir / "trajectory.jsonl", run_dir / "report.json"]
        if not all(path.exists() for path in required):
            continue
        task, steps, patch, test_log, report = load_run(run_dir)
        sft_plan.append(build_sft_plan(task, steps))
        if patch:
            sft_patch.append(build_sft_patch(task, patch))
            sft_debug.append(build_sft_debug(task, patch, test_log))
        reward_logs.append(build_reward_logs(report))

    write_jsonl(out / "sft_plan.jsonl", sft_plan)
    write_jsonl(out / "sft_patch.jsonl", sft_patch)
    write_jsonl(out / "sft_debug.jsonl", sft_debug)
    write_jsonl(out / "reward_logs.jsonl", reward_logs)
    typer.echo(
        json.dumps(
            {
                "sft_plan": len(sft_plan),
                "sft_patch": len(sft_patch),
                "sft_debug": len(sft_debug),
                "reward_logs": len(reward_logs),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    app()
