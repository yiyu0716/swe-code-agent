import json
from pathlib import Path

import typer

from swetrace.schema import FailureLabel, RunReport

app = typer.Typer(add_completion=False)


@app.command()
def main(
    runs: Path = typer.Option(Path("runs"), exists=True, file_okay=False, help="Run artifact root."),
    out: Path = typer.Option(
        Path("outputs/reports/manual_review_queue.jsonl"),
        help="Output JSONL path for human review.",
    ),
) -> None:
    rows = []
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        report_path = run_dir / "report.json"
        label_path = run_dir / "labels.json"
        if not report_path.exists() or not label_path.exists():
            continue
        report = RunReport.model_validate_json(report_path.read_text())
        if report.resolved:
            continue
        label = FailureLabel.model_validate_json(label_path.read_text())
        rows.append(review_item(run_dir, report, label))

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""))
    typer.echo(json.dumps({"review_items": len(rows), "out": str(out)}, ensure_ascii=False))


def review_item(run_dir: Path, report: RunReport, label: FailureLabel) -> dict:
    return {
        "run_id": report.run_id,
        "task_id": report.task_id,
        "status": report.status,
        "primary_failure": label.primary_failure,
        "secondary_failures": label.secondary_failures,
        "severity": label.severity,
        "needs_human_review": True,
        "is_data_usable_for_sft": label.is_data_usable_for_sft,
        "is_data_usable_for_dpo": label.is_data_usable_for_dpo,
        "num_steps": report.num_steps,
        "num_tool_calls": report.num_tool_calls,
        "patch_preview": _preview(run_dir / "patch.diff"),
        "test_log_preview": _preview(run_dir / "test.log"),
        "report_path": str(run_dir / "report.json"),
        "trajectory_path": str(run_dir / "trajectory.jsonl"),
        "label_path": str(run_dir / "labels.json"),
    }


def _preview(path: Path, limit: int = 1000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(errors="replace")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


if __name__ == "__main__":
    app()
