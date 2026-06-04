import json
import subprocess
import sys
from pathlib import Path

from swetrace.adapters.fake import FakeAdapter
from swetrace.artifacts import RunStore
from swetrace.schema import TaskSpec

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_fake_adapter_generates_complete_run(tmp_path) -> None:
    task = TaskSpec(
        task_id="fake-task",
        source="fake",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix add_one.",
        test_command="pytest",
    )
    store = RunStore(tmp_path)

    result = FakeAdapter().run_task(task, store)

    run_dir = tmp_path / result.run_id
    assert result.report.resolved is True
    assert (run_dir / "raw_agent.log").exists()
    assert (run_dir / "trajectory.jsonl").exists()
    assert (run_dir / "patch.diff").exists()
    assert (run_dir / "test.log").exists()
    assert (run_dir / "report.json").exists()


def test_run_task_cli_writes_artifacts(tmp_path) -> None:
    task_path = tmp_path / "task.json"
    task_path.write_text(
        json.dumps(
            {
                "task_id": "cli-task",
                "source": "fake",
                "repo": "owner/repo",
                "base_commit": "abc123",
                "issue_text": "Fix add_one.",
                "test_command": "pytest",
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.collect.run_task",
            "--task",
            str(task_path),
            "--agent",
            "fake",
            "--out",
            str(tmp_path / "runs"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    run_dir = tmp_path / "runs" / payload["run_id"]
    assert payload["status"] == "resolved"
    assert run_dir.exists()
    assert (run_dir / "report.json").exists()
