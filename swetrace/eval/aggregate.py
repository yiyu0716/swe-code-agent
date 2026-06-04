import csv
from pathlib import Path

from swetrace.schema import RunReport


def write_summary_csv(summary: dict[str, float | int], path: Path | str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def report_row(report: RunReport) -> dict[str, str | int | bool | None]:
    return {
        "run_id": report.run_id,
        "task_id": report.task_id,
        "agent": report.agent,
        "status": report.status,
        "patch_apply": report.patch_apply,
        "tests_passed": report.tests_passed,
        "resolved": report.resolved,
        "num_steps": report.num_steps,
        "num_tool_calls": report.num_tool_calls,
    }
