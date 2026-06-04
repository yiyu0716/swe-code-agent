import json
from pathlib import Path

import typer

from swetrace.adapters import FakeAdapter, MiniSweAgentAdapter
from swetrace.artifacts import RunStore
from swetrace.eval.aggregate import write_summary_csv
from swetrace.eval.metrics import summarize_reports
from swetrace.schema import TaskSpec

app = typer.Typer(add_completion=False)


def load_tasks(path: Path) -> list[TaskSpec]:
    tasks = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        tasks.append(TaskSpec.model_validate_json(line))
    return tasks


def get_adapter(agent: str, command_template: str | None = None):
    if agent == "fake":
        return FakeAdapter()
    if agent == "mini-swe-agent":
        return MiniSweAgentAdapter(command_template=command_template)
    raise typer.BadParameter(f"Unsupported agent: {agent}")


@app.command()
def main(
    tasks: Path = typer.Option(..., exists=True, readable=True, help="Path to tasks JSONL."),
    agent: str = typer.Option("fake", help="Adapter name."),
    out: Path = typer.Option(Path("runs"), help="Run artifact root."),
    summary: Path = typer.Option(Path("outputs/reports/summary.csv"), help="Summary CSV path."),
    command_template: str | None = typer.Option(
        None,
        help="External command template for real adapters. Supports {task_id} and {raw_dir}.",
    ),
) -> None:
    task_specs = load_tasks(tasks)
    store = RunStore(out)
    adapter = get_adapter(agent, command_template=command_template)
    reports = [adapter.run_task(task_spec, store).report for task_spec in task_specs]
    aggregate = summarize_reports(reports)
    write_summary_csv(aggregate, summary)
    typer.echo(json.dumps(aggregate, ensure_ascii=False))


if __name__ == "__main__":
    app()
