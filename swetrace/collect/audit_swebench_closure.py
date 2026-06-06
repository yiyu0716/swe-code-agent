import json
import subprocess
from pathlib import Path
from typing import Any

import typer

app = typer.Typer(add_completion=False)


def audit_closure(runs: Path, image_lines: list[str]) -> dict[str, Any]:
    downloaded_tasks = sorted({task_id for line in image_lines if (task_id := _task_id_from_image_line(line))})
    run_index = _index_runs(runs)

    missing_mini_run: list[str] = []
    without_nonempty_patch: list[str] = []
    without_official_eval: list[str] = []
    closed_tasks: list[str] = []

    for task_id in downloaded_tasks:
        records = run_index.get(task_id, [])
        if not records:
            missing_mini_run.append(task_id)
            without_nonempty_patch.append(task_id)
            without_official_eval.append(task_id)
            continue
        if not any(record["patch_nonempty"] for record in records):
            without_nonempty_patch.append(task_id)
        if not any(record["official_eval"] for record in records):
            without_official_eval.append(task_id)
        if any(record["official_eval"] for record in records):
            closed_tasks.append(task_id)

    nonempty_patch_missing_official = sorted(
        {
            record["task_id"]
            for records in run_index.values()
            for record in records
            if record["patch_nonempty"] and not record["official_eval"]
        }
    )
    pending_official = sorted(
        {
            record["task_id"]
            for records in run_index.values()
            for record in records
            if record["official_eval"] and not record["official_completed"]
        }
    )

    return {
        "latest_images": len(downloaded_tasks),
        "tasks_with_mini_run": len([task_id for task_id in downloaded_tasks if task_id in run_index]),
        "tasks_missing_mini_run": len(missing_mini_run),
        "tasks_without_nonempty_patch": len(without_nonempty_patch),
        "tasks_without_official_eval": len(without_official_eval),
        "closed_tasks": len(closed_tasks),
        "nonempty_patch_missing_official": len(nonempty_patch_missing_official),
        "pending_official": len(pending_official),
        "missing_mini_run": missing_mini_run,
        "without_nonempty_patch": without_nonempty_patch,
        "without_official_eval": without_official_eval,
        "nonempty_patch_missing_official_tasks": nonempty_patch_missing_official,
        "pending_official_tasks": pending_official,
    }


def has_open_closure_gaps(summary: dict[str, Any]) -> bool:
    return any(
        int(summary[key]) > 0
        for key in (
            "tasks_missing_mini_run",
            "tasks_without_official_eval",
            "nonempty_patch_missing_official",
        )
    )


def _task_id_from_image_line(line: str) -> str | None:
    token = line.strip().split(maxsplit=1)[0] if line.strip() else ""
    if not token:
        return None
    if ":" not in token:
        return None
    repository, tag = token.rsplit(":", 1)
    if tag != "latest":
        return None
    marker = "sweb.eval.x86_64."
    if marker not in repository:
        return None
    image_instance = repository.rsplit(marker, 1)[1]
    if "_1776_" not in image_instance:
        return None
    return image_instance.replace("_1776_", "__")


def _index_runs(runs: Path) -> dict[str, list[dict[str, Any]]]:
    by_task: dict[str, list[dict[str, Any]]] = {}
    if not runs.exists():
        return by_task
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        report_path = run_dir / "report.json"
        if not report_path.exists():
            continue
        try:
            report = json.loads(report_path.read_text())
        except json.JSONDecodeError:
            continue
        task_id = str(report.get("task_id") or "")
        if not task_id or task_id.startswith("fake-"):
            continue
        patch_path = run_dir / "patch.diff"
        official_path = run_dir / "official_eval.json"
        official_payload: dict[str, Any] = {}
        if official_path.exists():
            try:
                official_payload = json.loads(official_path.read_text())
            except json.JSONDecodeError:
                official_payload = {}
        by_task.setdefault(task_id, []).append(
            {
                "run_id": str(report.get("run_id") or run_dir.name),
                "task_id": task_id,
                "patch_nonempty": patch_path.exists()
                and bool(patch_path.read_text(errors="replace").strip()),
                "official_eval": official_path.exists(),
                "official_completed": bool(official_payload.get("completed")),
                "official_resolved": bool(official_payload.get("resolved")),
            }
        )
    return by_task


def _docker_image_lines() -> list[str]:
    completed = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}} {{.Size}}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise typer.BadParameter(completed.stderr.strip() or "docker images failed")
    return completed.stdout.splitlines()


@app.command()
def main(
    runs: Path = typer.Option(Path("/data/yiyuldx/swe/runs"), help="SWE-Trace runs root."),
    images_file: Path | None = typer.Option(
        None,
        exists=True,
        readable=True,
        help="Optional text file containing docker image lines. If omitted, docker images is used.",
    ),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Exit non-zero when closure gaps exist."),
) -> None:
    image_lines = images_file.read_text().splitlines() if images_file else _docker_image_lines()
    summary = audit_closure(runs=runs, image_lines=image_lines)
    typer.echo(json.dumps(summary, ensure_ascii=False))
    if strict and has_open_closure_gaps(summary):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
