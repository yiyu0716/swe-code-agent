import json
import subprocess
import sys
from pathlib import Path

from swetrace.data_builder.build_dpo_pairs import build_dpo_pairs, build_gold_dpo_pairs
from swetrace.data_builder.build_reward_logs import build_reward_logs
from swetrace.data_builder.build_sft import build_sft_debug, build_sft_patch, build_sft_plan
from swetrace.labeling.taxonomy import FAILURE_TAXONOMY, is_valid_failure_label
from swetrace.schema import RunReport, TaskSpec, TrajectoryStep

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_taxonomy_accepts_known_labels() -> None:
    assert "PatchError" in FAILURE_TAXONOMY
    assert is_valid_failure_label("PatchError.IncompleteFix") is True
    assert is_valid_failure_label("PatchError.Unknown") is False


def test_data_builders_emit_training_samples() -> None:
    task = TaskSpec(
        task_id="task-1",
        source="fake",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix add_one.",
        test_command="pytest",
        expected_files=["src/math_utils.py"],
    )
    steps = [
        TrajectoryStep(
            run_id="run-1",
            task_id=task.task_id,
            step_id=1,
            phase="plan",
            model_output="Inspect src/math_utils.py and update add_one.",
        ),
        TrajectoryStep(
            run_id="run-1",
            task_id=task.task_id,
            step_id=2,
            phase="edit",
            model_output="Patch add_one to return x + 1.",
            affected_files=["src/math_utils.py"],
            workspace_changed=True,
        ),
        TrajectoryStep(
            run_id="run-1",
            task_id=task.task_id,
            step_id=3,
            phase="test",
            model_output="Run pytest.",
            tool_result="1 passed",
        ),
    ]
    report = RunReport(
        run_id="run-1",
        task_id=task.task_id,
        agent="fake",
        status="resolved",
        patch_apply=True,
        tests_passed=True,
        resolved=True,
    )
    patch = "diff --git a/src/math_utils.py b/src/math_utils.py\n+def add_one(x): return x + 1\n"

    assert build_sft_plan(task, steps)["type"] == "sft_plan"
    assert build_sft_debug(task, patch, "1 passed")["type"] == "sft_debug"
    assert build_sft_patch(task, patch)["output"] == patch
    assert build_reward_logs(report)["reward"] > 0


def test_dpo_builder_pairs_successful_and_failed_patches() -> None:
    chosen = RunReport(
        run_id="chosen",
        task_id="task-1",
        agent="fake",
        status="resolved",
        patch_apply=True,
        tests_passed=True,
        resolved=True,
    )
    rejected = RunReport(
        run_id="rejected",
        task_id="task-1",
        agent="fake",
        status="failed",
        patch_apply=True,
        tests_passed=False,
        resolved=False,
    )

    pairs = build_dpo_pairs(
        prompt="issue + context",
        patches={"chosen": "good patch", "rejected": "bad patch"},
        reports=[chosen, rejected],
    )

    assert len(pairs) == 1
    assert pairs[0]["chosen"] == "good patch"
    assert pairs[0]["rejected_meta"]["resolved"] is False


def test_dpo_builder_pairs_gold_patch_with_failed_agent_patch() -> None:
    task = TaskSpec(
        task_id="task-1",
        source="swebench_lite",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix a real bug.",
        test_command="mini-swe-agent managed evaluation",
        gold_patch="gold patch",
    )
    rejected = RunReport(
        run_id="rejected",
        task_id="task-1",
        agent="mini-swe-agent",
        status="failed",
        patch_apply=True,
        tests_passed=False,
        resolved=False,
    )

    pairs = build_gold_dpo_pairs(
        tasks_by_run={"rejected": task},
        patches={"rejected": "agent patch"},
        reports=[rejected],
    )

    assert len(pairs) == 1
    assert pairs[0]["prompt"].startswith("Issue:\nFix a real bug.")
    assert pairs[0]["chosen"] == "gold patch"
    assert pairs[0]["chosen_meta"]["source"] == "swebench_gold_patch"
    assert pairs[0]["rejected"] == "agent patch"


def test_run_batch_cli_creates_multiple_reports_and_summary(tmp_path) -> None:
    tasks_path = tmp_path / "tasks.jsonl"
    rows = [
        {
            "task_id": "task-a",
            "source": "fake",
            "repo": "owner/repo",
            "base_commit": "abc123",
            "issue_text": "Fix a.",
            "test_command": "pytest",
        },
        {
            "task_id": "task-b",
            "source": "fake",
            "repo": "owner/repo",
            "base_commit": "abc123",
            "issue_text": "Fix b.",
            "test_command": "pytest",
        },
    ]
    tasks_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.collect.run_batch",
            "--tasks",
            str(tasks_path),
            "--agent",
            "fake",
            "--out",
            str(tmp_path / "runs"),
            "--summary",
            str(tmp_path / "summary.csv"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["num_runs"] == 2
    assert (tmp_path / "summary.csv").exists()
    assert "resolved_rate" in (tmp_path / "summary.csv").read_text()
