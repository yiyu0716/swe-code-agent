import json
import subprocess
import sys
from pathlib import Path

from swetrace.data_builder.export_official_v02 import export_official_v02


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_export_official_v02_uses_only_completed_official_labels(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "resolved-run",
        "task-resolved",
        agent_patch="resolved patch",
        official={"completed": True, "resolved": True, "patch_successfully_applied": True},
    )
    _write_run(
        runs,
        "unresolved-run",
        "task-unresolved",
        agent_patch="unresolved patch",
        official={"completed": True, "resolved": False, "patch_successfully_applied": True},
    )
    _write_run(
        runs,
        "pending-run",
        "task-pending",
        agent_patch="pending patch",
        official={"completed": False, "resolved": False, "patch_successfully_applied": False},
    )
    _write_run(
        runs,
        "untrusted-run",
        "task-untrusted",
        agent_patch="untrusted patch",
        official=None,
    )

    summary = export_official_v02(
        runs=runs,
        out=tmp_path / "datasets" / "v0.2",
        version="v0.2-test",
    )

    assert summary["sft_patch"] == 1
    assert summary["dpo_main"] == 1
    assert summary["debug_cases"] == 1
    assert summary["reward_logs"] == 2
    assert summary["excluded"] == 2
    assert summary["train_ready"] is False

    sft_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "sft_patch.jsonl")
    dpo_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "dpo_main.jsonl")
    reward_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "reward_logs.jsonl")
    excluded_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "excluded.jsonl")
    manifest = json.loads((tmp_path / "datasets" / "v0.2" / "manifest.json").read_text())

    assert sft_rows[0]["output"] == "resolved patch"
    assert sft_rows[0]["meta"]["official_resolved"] is True
    assert sft_rows[0]["meta"]["legacy_status"] == "failed"
    assert sft_rows[0]["meta"]["legacy_resolved"] is False
    assert dpo_rows[0]["chosen"] == "gold patch for task-unresolved"
    assert dpo_rows[0]["rejected"] == "unresolved patch"
    assert dpo_rows[0]["meta"]["official_resolved"] is False
    assert {row["reward"] for row in reward_rows} == {1.0, 0.0}
    assert {row["reason"] for row in excluded_rows} == {
        "official_eval_pending",
        "missing_official_eval",
    }
    assert manifest["version"] == "v0.2-test"
    assert manifest["quality_gate"]["requires_official_eval"] is True


def test_export_official_v02_reports_train_ready_when_minimum_counts_are_met(tmp_path) -> None:
    runs = tmp_path / "runs"
    for index in range(2):
        _write_run(
            runs,
            f"resolved-{index}",
            f"task-resolved-{index}",
            agent_patch=f"resolved patch {index}",
            official={"completed": True, "resolved": True, "patch_successfully_applied": True},
        )
    for index in range(3):
        _write_run(
            runs,
            f"unresolved-{index}",
            f"task-unresolved-{index}",
            agent_patch=f"unresolved patch {index}",
            official={"completed": True, "resolved": False, "patch_successfully_applied": True},
        )

    summary = export_official_v02(
        runs=runs,
        out=tmp_path / "datasets" / "v0.2",
        min_sft=2,
        min_dpo=3,
    )

    assert summary["train_ready"] is True


def test_export_official_v02_prefers_resolved_agent_patch_for_same_task_dpo(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "agent-resolved",
        "task-shared",
        agent_patch="agent resolved patch",
        official={"completed": True, "resolved": True, "patch_successfully_applied": True},
    )
    _write_run(
        runs,
        "agent-unresolved",
        "task-shared",
        agent_patch="agent unresolved patch",
        official={"completed": True, "resolved": False, "patch_successfully_applied": True},
    )

    summary = export_official_v02(
        runs=runs,
        out=tmp_path / "datasets" / "v0.2",
        version="v0.2-test",
    )

    dpo_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "dpo_main.jsonl")

    assert summary["dpo_main"] == 1
    assert dpo_rows[0]["chosen"] == "agent resolved patch"
    assert dpo_rows[0]["chosen_meta"]["source"] == "agent_resolved_patch"
    assert dpo_rows[0]["chosen_meta"]["run_id"] == "agent-resolved"
    assert dpo_rows[0]["rejected"] == "agent unresolved patch"


def test_export_official_v02_deduplicates_exact_training_rows(tmp_path) -> None:
    runs = tmp_path / "runs"
    for index in range(2):
        _write_run(
            runs,
            f"resolved-duplicate-{index}",
            f"task-resolved-duplicate-{index}",
            agent_patch="same resolved patch",
            official={"completed": True, "resolved": True, "patch_successfully_applied": True},
        )
        _write_run(
            runs,
            f"unresolved-duplicate-{index}",
            "task-unresolved-duplicate",
            agent_patch="same unresolved patch",
            official={"completed": True, "resolved": False, "patch_successfully_applied": True},
        )

    summary = export_official_v02(
        runs=runs,
        out=tmp_path / "datasets" / "v0.2",
        version="v0.2-test",
    )

    sft_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "sft_patch.jsonl")
    dpo_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "dpo_main.jsonl")
    excluded_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "excluded.jsonl")

    assert summary["sft_patch"] == 1
    assert summary["sft_plan"] == 1
    assert summary["dpo_main"] == 1
    assert summary["debug_cases"] == 1
    assert sft_rows[0]["output"] == "same resolved patch"
    assert dpo_rows[0]["rejected"] == "same unresolved patch"
    assert {row["reason"] for row in excluded_rows} == {
        "duplicate_sft_patch",
        "duplicate_dpo_pair",
    }


def test_export_official_v02_reward_logs_expose_official_tests_passed(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "resolved-run",
        "task-resolved",
        agent_patch="resolved patch",
        official={"completed": True, "resolved": True, "patch_successfully_applied": True},
    )
    _write_run(
        runs,
        "unresolved-run",
        "task-unresolved",
        agent_patch="unresolved patch",
        official={"completed": True, "resolved": False, "patch_successfully_applied": True},
    )

    export_official_v02(
        runs=runs,
        out=tmp_path / "datasets" / "v0.2",
        version="v0.2-test",
    )

    reward_rows = _read_jsonl(tmp_path / "datasets" / "v0.2" / "reward_logs.jsonl")
    by_task = {row["task_id"]: row for row in reward_rows}

    assert by_task["task-resolved"]["tests_passed"] is True
    assert by_task["task-resolved"]["resolved"] is True
    assert by_task["task-unresolved"]["tests_passed"] is False
    assert by_task["task-unresolved"]["resolved"] is False


def test_export_official_v02_cli_writes_versioned_dataset(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(
        runs,
        "resolved-run",
        "task-resolved",
        agent_patch="resolved patch",
        official={"completed": True, "resolved": True, "patch_successfully_applied": True},
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.data_builder.export_official_v02",
            "--runs",
            str(runs),
            "--out",
            str(tmp_path / "datasets" / "v0.2"),
            "--version",
            "v0.2-cli",
            "--min-sft",
            "1",
            "--min-dpo",
            "0",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["version"] == "v0.2-cli"
    assert payload["train_ready"] is True
    assert (tmp_path / "datasets" / "v0.2" / "sft_patch.jsonl").exists()


def _write_run(
    runs: Path,
    run_id: str,
    task_id: str,
    *,
    agent_patch: str,
    official: dict | None,
) -> None:
    run_dir = runs / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "source": "swebench_lite",
                "repo": "owner/repo",
                "base_commit": "abc123",
                "issue_text": f"Fix {task_id}.",
                "test_command": "mini-swe-agent managed evaluation",
                "expected_files": ["src/file.py"],
                "gold_patch": f"gold patch for {task_id}",
            }
        )
    )
    (run_dir / "trajectory.jsonl").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "task_id": task_id,
                "step_id": 1,
                "phase": "plan",
                "model_output": "Inspect the failing test.",
            }
        )
        + "\n"
    )
    (run_dir / "patch.diff").write_text(agent_patch)
    (run_dir / "test.log").write_text("official harness owns the final label\n")
    (run_dir / "report.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "task_id": task_id,
                "agent": "mini-swe-agent",
                "status": "resolved" if official and official["resolved"] else "failed",
                "patch_apply": True,
                "tests_passed": bool(official and official["resolved"]),
                "resolved": bool(official and official["resolved"]),
                "num_tool_calls": 3,
                "label_source": "swebench_official" if official else "mini_swe_agent",
                "legacy_status": "failed" if official else None,
                "legacy_patch_apply": True if official else None,
                "legacy_tests_passed": False if official else None,
                "legacy_resolved": False if official else None,
            }
        )
    )
    if official is not None:
        payload = {
            "source": "swebench_official",
            "run_id": run_id,
            "task_id": task_id,
            "official_run_id": "official-test",
            "completed": bool(official["completed"]),
            "patch_exists": True,
            "patch_successfully_applied": bool(official["patch_successfully_applied"]),
            "tests_passed": bool(official["completed"] and official["resolved"]),
            "resolved": bool(official["resolved"]),
            "fail_to_pass_success": 1 if official["resolved"] else 0,
            "fail_to_pass_failure": 0 if official["resolved"] else 1,
            "pass_to_pass_success": 2,
            "pass_to_pass_failure": 0,
            "report_path": "/tmp/report.json",
        }
        (run_dir / "official_eval.json").write_text(json.dumps(payload))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
