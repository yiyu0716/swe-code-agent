import json
from datetime import UTC, datetime
from pathlib import Path

import typer

from swetrace.schema import ReviewAnnotation, RunReport, TaskSpec

app = typer.Typer(add_completion=False)


DEFAULT_ANNOTATIONS = Path("/data/yiyuldx/swe/outputs/reports/manual_annotations.jsonl")
DEFAULT_RUNS = Path("/data/yiyuldx/swe/runs")
DEFAULT_OUT = Path("/data/yiyuldx/swe/outputs/datasets/v0.1")


def export_filtered_dpo(
    annotations: Path = DEFAULT_ANNOTATIONS,
    runs: Path = DEFAULT_RUNS,
    out: Path = DEFAULT_OUT,
    version: str = "v0.1",
) -> dict:
    annotation_rows = [
        ReviewAnnotation.model_validate(row)
        for row in _read_jsonl(annotations)
    ]
    dpo_main = []
    dpo_hard_negative = []
    sft_sanity = []
    excluded = []

    for annotation in annotation_rows:
        run_dir = runs / annotation.run_id
        task = TaskSpec.model_validate(_read_json(run_dir / "task.json"))
        report = RunReport.model_validate(_read_json(run_dir / "report.json"))
        agent_patch = _read_text(run_dir / "patch.diff")
        base_meta = _meta(annotation=annotation, report=report, task=task)

        if annotation.sft_usable:
            sft_sanity.append(
                {
                    "type": "sft_sanity",
                    "prompt": _task_prompt(task),
                    "output": agent_patch,
                    "meta": base_meta,
                }
            )
            continue

        if not annotation.dpo_usable:
            excluded.append({**base_meta, "reason": "dpo_usable=false"})
            continue
        if not task.gold_patch or not agent_patch.strip():
            excluded.append({**base_meta, "reason": "missing gold or agent patch"})
            continue

        row = {
            "type": "dpo_pair",
            "prompt": _task_prompt(task),
            "chosen": task.gold_patch,
            "rejected": agent_patch,
            "meta": base_meta,
        }
        if annotation.patch_quality == "poor":
            dpo_hard_negative.append(row)
        elif annotation.patch_quality in {"close", "partial"}:
            dpo_main.append(row)
        else:
            excluded.append({**base_meta, "reason": f"unsupported patch_quality={annotation.patch_quality}"})

    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "dpo_main.jsonl", dpo_main)
    _write_jsonl(out / "dpo_hard_negative.jsonl", dpo_hard_negative)
    _write_jsonl(out / "sft_sanity.jsonl", sft_sanity)
    _write_jsonl(out / "excluded.jsonl", excluded)
    manifest = {
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "source_annotations": str(annotations),
        "source_runs": str(runs),
        "out": str(out),
        "rules": {
            "dpo_main": "dpo_usable=true and patch_quality in {close, partial}",
            "dpo_hard_negative": "dpo_usable=true and patch_quality=poor",
            "sft_sanity": "sft_usable=true",
            "excluded": "environment, empty, missing patch, or ambiguous DPO target",
        },
        "counts": {
            "annotations": len(annotation_rows),
            "dpo_main": len(dpo_main),
            "dpo_hard_negative": len(dpo_hard_negative),
            "sft_sanity": len(sft_sanity),
            "excluded": len(excluded),
        },
        "files": {
            "dpo_main": str(out / "dpo_main.jsonl"),
            "dpo_hard_negative": str(out / "dpo_hard_negative.jsonl"),
            "sft_sanity": str(out / "sft_sanity.jsonl"),
            "excluded": str(out / "excluded.jsonl"),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest["counts"] | {"out": str(out), "version": version}


@app.command()
def main(
    annotations: Path = typer.Option(DEFAULT_ANNOTATIONS, exists=True, readable=True),
    runs: Path = typer.Option(DEFAULT_RUNS, exists=True, file_okay=False),
    out: Path = typer.Option(DEFAULT_OUT),
    version: str = typer.Option("v0.1"),
) -> None:
    typer.echo(
        json.dumps(
            export_filtered_dpo(
                annotations=annotations,
                runs=runs,
                out=out,
                version=version,
            ),
            ensure_ascii=False,
        )
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        + ("\n" if rows else "")
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="replace")


def _task_prompt(task: TaskSpec) -> str:
    expected = ", ".join(task.expected_files)
    return (
        f"Issue:\n{task.issue_text}\n\n"
        f"Repository: {task.repo}\n"
        f"Base commit: {task.base_commit}\n"
        f"Expected files: {expected}\n"
        f"Test command: {task.test_command}"
    )


def _meta(annotation: ReviewAnnotation, report: RunReport, task: TaskSpec) -> dict:
    return {
        "run_id": annotation.run_id,
        "task_id": annotation.task_id,
        "repo": task.repo,
        "source": task.source,
        "status": report.status,
        "resolved": report.resolved,
        "patch_apply": report.patch_apply,
        "tests_passed": report.tests_passed,
        "patch_quality": annotation.patch_quality,
        "human_failure": annotation.human_failure,
        "sft_usable": annotation.sft_usable,
        "dpo_usable": annotation.dpo_usable,
        "notes": annotation.notes,
        "reviewer": annotation.reviewer,
    }


if __name__ == "__main__":
    app()
