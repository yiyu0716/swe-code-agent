import json
from pathlib import Path

import typer

from swetrace.collect.select_swebench_tasks import load_swebench_rows, row_to_task
from swetrace.schema import TaskSpec

app = typer.Typer(add_completion=False)


@app.command()
def main(
    dataset: Path = typer.Option(..., exists=True, file_okay=False, help="Local SWE-bench dataset root."),
    runs: Path = typer.Option(Path("runs"), exists=True, file_okay=False, help="Run artifact root."),
    split: str = typer.Option("dev", help="Dataset split name."),
) -> None:
    tasks = {task.task_id: task for task in (row_to_task(row) for row in load_swebench_rows(dataset, split))}
    updated = 0
    skipped = 0
    for task_path in sorted(runs.glob("*/task.json")):
        current = TaskSpec.model_validate_json(task_path.read_text())
        enriched = tasks.get(current.task_id)
        if enriched is None:
            skipped += 1
            continue
        task_path.write_text(json.dumps(enriched.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n")
        updated += 1

    typer.echo(json.dumps({"updated_tasks": updated, "skipped_tasks": skipped}, ensure_ascii=False))


if __name__ == "__main__":
    app()
