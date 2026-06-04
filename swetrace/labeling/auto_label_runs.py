import json
from pathlib import Path

import typer

from swetrace.labeling.rule_labeler import label_run
from swetrace.schema import RunReport

app = typer.Typer(add_completion=False)


@app.command()
def main(
    runs: Path = typer.Option(Path("runs"), exists=True, file_okay=False, help="Run artifact root."),
) -> None:
    count = 0
    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        report_path = run_dir / "report.json"
        if not report_path.exists():
            continue
        report = RunReport.model_validate_json(report_path.read_text())
        raw_log_path = run_dir / "raw_agent.log"
        raw_log = raw_log_path.read_text() if raw_log_path.exists() else ""
        label = label_run(report, raw_log=raw_log)
        (run_dir / "labels.json").write_text(
            json.dumps(label.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
        )
        count += 1
    typer.echo(json.dumps({"labeled_runs": count}, ensure_ascii=False))


if __name__ == "__main__":
    app()
