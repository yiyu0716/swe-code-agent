import json
from pathlib import Path

import typer

from swetrace.schema import ReviewAnnotation

app = typer.Typer(add_completion=False)


@app.command()
def main(
    queue: Path = typer.Option(
        Path("/data/yiyuldx/swe/outputs/reports/manual_review_queue.jsonl"),
        exists=True,
        readable=True,
        help="Manual review queue JSONL path.",
    ),
    out: Path = typer.Option(
        Path("/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl"),
        help="Output JSONL path for human annotations.",
    ),
    run_id: str = typer.Option(..., help="Run ID to annotate."),
    human_failure: str = typer.Option(..., help="Human-confirmed primary failure."),
    patch_quality: str = typer.Option(..., help="Human patch-quality bucket."),
    sft_usable: str = typer.Option(..., help="Whether this run is usable for SFT."),
    dpo_usable: str = typer.Option(..., help="Whether this run is usable for DPO."),
    notes: str | None = typer.Option(None, help="Free-form review note."),
    reviewer: str = typer.Option("manual", help="Reviewer name or source."),
) -> None:
    queue_rows = _read_jsonl(queue)
    queue_row = next((row for row in queue_rows if row.get("run_id") == run_id), None)
    if queue_row is None:
        raise typer.BadParameter(f"run_id not found in review queue: {run_id}", param_hint="--run-id")

    annotation = ReviewAnnotation(
        run_id=run_id,
        task_id=str(queue_row.get("task_id") or ""),
        auto_primary_failure=str(queue_row.get("primary_failure") or ""),
        auto_severity=int(queue_row.get("severity") or 1),
        human_failure=human_failure,
        patch_quality=patch_quality,
        sft_usable=_parse_bool(sft_usable, option_name="--sft-usable"),
        dpo_usable=_parse_bool(dpo_usable, option_name="--dpo-usable"),
        notes=notes,
        reviewer=reviewer,
    )

    annotations = [
        ReviewAnnotation.model_validate(row)
        for row in (_read_jsonl(out) if out.exists() else [])
        if row.get("run_id") != run_id
    ]
    annotations.append(annotation)
    annotations.sort(key=lambda row: row.run_id)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "\n".join(
            json.dumps(row.model_dump(mode="json"), ensure_ascii=False) for row in annotations
        )
        + ("\n" if annotations else "")
    )
    typer.echo(
        json.dumps(
            {"annotations": len(annotations), "updated": run_id, "out": str(out)},
            ensure_ascii=False,
        )
    )


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _parse_bool(value: str, option_name: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    raise typer.BadParameter(f"expected true or false, got: {value}", param_hint=option_name)


if __name__ == "__main__":
    app()
