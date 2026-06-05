import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from swetrace.data_builder.build_sft import build_sft_patch, build_sft_plan
from swetrace.schema import RunReport, TaskSpec, TrajectoryStep

app = typer.Typer(add_completion=False)

DEFAULT_RUNS = Path("/data/yiyuldx/swe/runs")
DEFAULT_OUT = Path("/data/yiyuldx/swe/outputs/datasets/v0.2")


def export_official_v02(
    runs: Path = DEFAULT_RUNS,
    out: Path = DEFAULT_OUT,
    version: str = "v0.2",
    min_sft: int = 30,
    min_dpo: int = 60,
) -> dict[str, Any]:
    sft_plan: list[dict[str, Any]] = []
    sft_patch: list[dict[str, Any]] = []
    dpo_main: list[dict[str, Any]] = []
    debug_cases: list[dict[str, Any]] = []
    reward_logs: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for run_dir in sorted(path for path in runs.iterdir() if path.is_dir()):
        required = [run_dir / "task.json", run_dir / "report.json"]
        if not all(path.exists() for path in required):
            continue
        task = TaskSpec.model_validate(_read_json(run_dir / "task.json"))
        report = RunReport.model_validate(_read_json(run_dir / "report.json"))
        official = _read_optional_json(run_dir / "official_eval.json")
        patch = _read_text(run_dir / "patch.diff")
        steps = _read_steps(run_dir / "trajectory.jsonl")
        base_meta = _meta(task=task, report=report, official=official, run_dir=run_dir)

        if task.task_id.startswith("fake-") or task.source == "fake":
            excluded.append({**base_meta, "reason": "fake_or_synthetic"})
            continue
        if official is None:
            excluded.append({**base_meta, "reason": "missing_official_eval"})
            continue
        if not official.get("completed"):
            excluded.append({**base_meta, "reason": "official_eval_pending"})
            continue
        if not patch.strip():
            excluded.append({**base_meta, "reason": "empty_agent_patch"})
            continue
        if not official.get("patch_successfully_applied"):
            excluded.append({**base_meta, "reason": "official_patch_apply_failed"})
            continue

        reward_logs.append(_reward_log(base_meta))
        if official.get("resolved"):
            plan = build_sft_plan(task, steps)
            plan["meta"] = base_meta
            sft_plan.append(plan)
            patch_row = build_sft_patch(task, patch)
            patch_row["meta"] = base_meta
            sft_patch.append(patch_row)
            continue

        if not task.gold_patch:
            excluded.append({**base_meta, "reason": "missing_gold_patch"})
            continue
        dpo_main.append(
            {
                "type": "dpo_pair",
                "prompt": _task_prompt(task),
                "chosen": task.gold_patch,
                "rejected": patch,
                "meta": base_meta,
                "chosen_meta": {
                    "source": "swebench_gold_patch",
                    "task_id": task.task_id,
                    "repo": task.repo,
                    "resolved": True,
                    "tests_passed": True,
                },
                "rejected_meta": base_meta,
            }
        )
        debug_cases.append(
            {
                "type": "debug_case",
                "prompt": _task_prompt(task),
                "agent_patch": patch,
                "gold_patch": task.gold_patch,
                "official_fail_to_pass_failure": int(official.get("fail_to_pass_failure") or 0),
                "official_pass_to_pass_failure": int(official.get("pass_to_pass_failure") or 0),
                "meta": base_meta,
            }
        )

    out.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out / "sft_plan.jsonl", sft_plan)
    _write_jsonl(out / "sft_patch.jsonl", sft_patch)
    _write_jsonl(out / "dpo_main.jsonl", dpo_main)
    _write_jsonl(out / "debug_cases.jsonl", debug_cases)
    _write_jsonl(out / "reward_logs.jsonl", reward_logs)
    _write_jsonl(out / "excluded.jsonl", excluded)

    train_ready = len(sft_patch) >= min_sft and len(dpo_main) >= min_dpo
    manifest = {
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "source_runs": str(runs),
        "out": str(out),
        "quality_gate": {
            "requires_official_eval": True,
            "sft_rule": "official completed + patch applied + resolved",
            "dpo_rule": "official completed + patch applied + unresolved + gold patch",
            "excluded_rule": "fake, pending, missing official eval, empty patch, patch apply fail, or missing gold",
            "min_sft": min_sft,
            "min_dpo": min_dpo,
        },
        "counts": {
            "sft_plan": len(sft_plan),
            "sft_patch": len(sft_patch),
            "dpo_main": len(dpo_main),
            "debug_cases": len(debug_cases),
            "reward_logs": len(reward_logs),
            "excluded": len(excluded),
            "train_ready": train_ready,
        },
        "files": {
            "sft_plan": str(out / "sft_plan.jsonl"),
            "sft_patch": str(out / "sft_patch.jsonl"),
            "dpo_main": str(out / "dpo_main.jsonl"),
            "debug_cases": str(out / "debug_cases.jsonl"),
            "reward_logs": str(out / "reward_logs.jsonl"),
            "excluded": str(out / "excluded.jsonl"),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest["counts"] | {"out": str(out), "version": version}


@app.command()
def main(
    runs: Path = typer.Option(DEFAULT_RUNS, exists=True, file_okay=False),
    out: Path = typer.Option(DEFAULT_OUT),
    version: str = typer.Option("v0.2"),
    min_sft: int = typer.Option(30, min=0),
    min_dpo: int = typer.Option(60, min=0),
) -> None:
    typer.echo(
        json.dumps(
            export_official_v02(
                runs=runs,
                out=out,
                version=version,
                min_sft=min_sft,
                min_dpo=min_dpo,
            ),
            ensure_ascii=False,
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return _read_json(path)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="replace")


def _read_steps(path: Path) -> list[TrajectoryStep]:
    if not path.exists():
        return []
    return [
        TrajectoryStep.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
        + ("\n" if rows else "")
    )


def _task_prompt(task: TaskSpec) -> str:
    expected = ", ".join(task.expected_files)
    return (
        f"Issue:\n{task.issue_text}\n\n"
        f"Repository: {task.repo}\n"
        f"Base commit: {task.base_commit}\n"
        f"Expected files: {expected}\n"
        f"Test command: {task.test_command}"
    )


def _meta(
    task: TaskSpec,
    report: RunReport,
    official: dict[str, Any] | None,
    run_dir: Path,
) -> dict[str, Any]:
    official_completed = bool(official.get("completed")) if official else False
    official_resolved = bool(official.get("resolved")) if official else False
    official_patch_applied = bool(official.get("patch_successfully_applied")) if official else False
    return {
        "run_id": report.run_id,
        "task_id": report.task_id,
        "repo": task.repo,
        "source": task.source,
        "run_dir": str(run_dir),
        "legacy_status": report.status,
        "legacy_resolved": report.resolved,
        "legacy_tests_passed": report.tests_passed,
        "official_completed": official_completed,
        "official_resolved": official_resolved,
        "official_patch_successfully_applied": official_patch_applied,
        "official_fail_to_pass_success": int((official or {}).get("fail_to_pass_success") or 0),
        "official_fail_to_pass_failure": int((official or {}).get("fail_to_pass_failure") or 0),
        "official_pass_to_pass_success": int((official or {}).get("pass_to_pass_success") or 0),
        "official_pass_to_pass_failure": int((official or {}).get("pass_to_pass_failure") or 0),
        "official_report_path": (official or {}).get("report_path"),
        "num_steps": report.num_steps,
        "num_tool_calls": report.num_tool_calls,
    }


def _reward_log(meta: dict[str, Any]) -> dict[str, Any]:
    resolved = bool(meta["official_resolved"])
    reward = 1.0 if resolved else 0.0
    return {
        "type": "official_reward_log",
        "run_id": meta["run_id"],
        "task_id": meta["task_id"],
        "reward": reward,
        "official_completed": meta["official_completed"],
        "official_resolved": resolved,
        "official_patch_successfully_applied": meta["official_patch_successfully_applied"],
        "meta": meta,
    }


if __name__ == "__main__":
    app()
