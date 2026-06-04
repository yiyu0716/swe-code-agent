import json
import re
from pathlib import Path

import typer

from swetrace.schema import TaskSpec

app = typer.Typer(add_completion=False)


def load_swebench_rows(dataset: Path, split: str) -> list[dict]:
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover - exercised only on incomplete envs.
        raise typer.BadParameter("Reading SWE-bench parquet requires pandas/pyarrow.") from exc

    parquet_path = dataset / "data" / f"{split}-00000-of-00001.parquet"
    if not parquet_path.exists():
        raise typer.BadParameter(f"Missing SWE-bench parquet: {parquet_path}")
    return pd.read_parquet(parquet_path).to_dict(orient="records")


def row_to_task(row: dict) -> TaskSpec:
    instance_id = str(row["instance_id"])
    return TaskSpec(
        task_id=instance_id,
        source="swebench_lite",
        repo=str(row["repo"]),
        base_commit=str(row.get("base_commit") or "unknown"),
        issue_text=str(row.get("problem_statement") or ""),
        test_command="mini-swe-agent managed evaluation",
        expected_files=extract_patch_files(str(row.get("patch") or "")),
        gold_patch=str(row.get("patch") or "") or None,
        difficulty="medium",
        tags=["swebench-lite", f"version:{row.get('version')}", "real-agent-batch"],
    )


def extract_patch_files(patch: str) -> list[str]:
    paths: list[str] = []
    for match in re.finditer(r"^diff --git a/(.*?) b/", patch, flags=re.MULTILINE):
        path = match.group(1)
        if path not in paths:
            paths.append(path)
    return paths


@app.command()
def main(
    dataset: Path = typer.Option(..., exists=True, file_okay=False, help="Local SWE-bench dataset root."),
    split: str = typer.Option("dev", help="Dataset split name."),
    out: Path = typer.Option(..., help="Output tasks JSONL path."),
    repo: str | None = typer.Option(None, help="Optional repo filter, e.g. sqlfluff/sqlfluff."),
    limit: int = typer.Option(10, min=1, help="Maximum tasks to export."),
    skip_existing: Path | None = typer.Option(
        None,
        exists=True,
        file_okay=False,
        help="Optional runs root; task ids with existing reports are skipped.",
    ),
) -> None:
    completed_task_ids = _completed_task_ids(skip_existing) if skip_existing else set()
    selected: list[TaskSpec] = []
    for row in load_swebench_rows(dataset, split):
        if repo and row.get("repo") != repo:
            continue
        if row.get("instance_id") in completed_task_ids:
            continue
        selected.append(row_to_task(row))
        if len(selected) >= limit:
            break

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(task.model_dump_json() for task in selected) + ("\n" if selected else ""))
    typer.echo(json.dumps({"selected_tasks": len(selected), "out": str(out)}, ensure_ascii=False))


def _completed_task_ids(runs: Path) -> set[str]:
    task_ids = set()
    for report_path in runs.glob("*/report.json"):
        try:
            report = json.loads(report_path.read_text())
        except json.JSONDecodeError:
            continue
        task_id = report.get("task_id")
        if isinstance(task_id, str):
            task_ids.add(task_id)
    return task_ids


if __name__ == "__main__":
    app()
