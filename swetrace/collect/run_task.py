import json
from pathlib import Path

import typer

from swetrace.adapters import FakeAdapter
from swetrace.artifacts import RunStore
from swetrace.schema import TaskSpec

app = typer.Typer(add_completion=False)


def load_task(path: Path) -> TaskSpec:
    return TaskSpec.model_validate_json(path.read_text())


def get_adapter(agent: str):
    if agent == "fake":
        return FakeAdapter()
    raise typer.BadParameter(f"Unsupported agent: {agent}")


@app.command()
def main(
    task: Path = typer.Option(..., exists=True, readable=True, help="Path to task JSON."),
    agent: str = typer.Option("fake", help="Adapter name."),
    out: Path = typer.Option(Path("runs"), help="Run artifact root."),
) -> None:
    task_spec = load_task(task)
    store = RunStore(out)
    adapter = get_adapter(agent)
    result = adapter.run_task(task_spec, store)
    typer.echo(
        json.dumps(
            {
                "run_id": result.run_id,
                "task_id": result.report.task_id,
                "agent": result.report.agent,
                "status": result.report.status,
                "run_dir": str(store.run_dir(result.run_id)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    app()
