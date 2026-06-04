import json
import subprocess
from pathlib import Path

import typer

from swetrace.collect.run_batch import load_tasks
from swetrace.schema import TaskSpec

app = typer.Typer(add_completion=False)


def swebench_image_for_task(task: TaskSpec) -> str:
    docker_compatible = task.task_id.replace("__", "_1776_")
    return f"docker.io/swebench/sweb.eval.x86_64.{docker_compatible}:latest".lower()


@app.command()
def main(
    tasks: Path = typer.Option(..., exists=True, readable=True, help="Tasks JSONL path."),
    out: Path = typer.Option(Path("outputs/reports/swebench_images.jsonl"), help="Image manifest path."),
    dry_run: bool = typer.Option(False, help="Only write planned image names; do not pull."),
    timeout_seconds: int = typer.Option(900, min=1, help="docker pull timeout per image."),
) -> None:
    task_specs = load_tasks(tasks)
    rows = []
    pulled = 0
    failed = 0
    for task in task_specs:
        image = swebench_image_for_task(task)
        if dry_run:
            row = _manifest_row(task.task_id, image, "planned", None, "")
        else:
            completed = subprocess.run(
                ["docker", "pull", image],
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            status = "pulled" if completed.returncode == 0 else "failed"
            pulled += int(status == "pulled")
            failed += int(status == "failed")
            row = _manifest_row(
                task.task_id,
                image,
                status,
                completed.returncode,
                _clip_log(completed.stdout + "\n" + completed.stderr),
            )
        rows.append(row)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""))
    typer.echo(
        json.dumps(
            {"planned": len(rows), "pulled": pulled, "failed": failed, "out": str(out)},
            ensure_ascii=False,
        )
    )


def _manifest_row(
    task_id: str,
    image: str,
    status: str,
    returncode: int | None,
    log_preview: str,
) -> dict[str, str | int | None]:
    return {
        "task_id": task_id,
        "image": image,
        "status": status,
        "returncode": returncode,
        "log_preview": log_preview,
    }


def _clip_log(text: str, limit: int = 500) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


if __name__ == "__main__":
    app()
