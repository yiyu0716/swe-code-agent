import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_build_data_cli_exports_sft_and_reward_logs(tmp_path) -> None:
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": "task-1",
                "source": "fake",
                "repo": "owner/repo",
                "base_commit": "abc123",
                "issue_text": "Fix add_one.",
                "test_command": "pytest",
                "expected_files": ["src/math_utils.py"],
            }
        )
    )
    (run_dir / "trajectory.jsonl").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "task_id": "task-1",
                "step_id": 1,
                "phase": "plan",
                "model_output": "Inspect src/math_utils.py.",
            }
        )
        + "\n"
    )
    (run_dir / "patch.diff").write_text("diff --git a/src/math_utils.py b/src/math_utils.py\n")
    (run_dir / "test.log").write_text("1 passed\n")
    (run_dir / "report.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "task_id": "task-1",
                "agent": "fake",
                "status": "resolved",
                "patch_apply": True,
                "tests_passed": True,
                "resolved": True,
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.data_builder.build_from_runs",
            "--runs",
            str(tmp_path / "runs"),
            "--out",
            str(tmp_path / "datasets"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["sft_plan"] == 1
    assert (tmp_path / "datasets" / "sft_plan.jsonl").exists()
    assert (tmp_path / "datasets" / "reward_logs.jsonl").exists()
