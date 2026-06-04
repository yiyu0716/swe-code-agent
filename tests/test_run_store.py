import json

from swetrace.artifacts import RunStore
from swetrace.schema import RunReport, TaskSpec, TrajectoryStep


def test_run_store_writes_replayable_artifacts(tmp_path) -> None:
    store = RunStore(tmp_path)
    task = TaskSpec(
        task_id="task-1",
        source="fake",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix it.",
        test_command="pytest",
    )
    run_id = store.create_run(task, agent="fake")
    steps = [
        TrajectoryStep(
            run_id=run_id,
            task_id=task.task_id,
            step_id=1,
            phase="plan",
            model_output="Inspect the failing test.",
        )
    ]
    report = RunReport(
        run_id=run_id,
        task_id=task.task_id,
        agent="fake",
        status="failed",
        patch_apply=False,
        tests_passed=False,
        resolved=False,
        stop_reason="final",
    )

    store.write_trajectory(run_id, steps)
    store.write_text(run_id, "patch.diff", "diff --git a/file b/file\n")
    store.write_text(run_id, "test.log", "1 failed\n")
    store.write_report(report)

    run_dir = tmp_path / run_id
    assert (run_dir / "task.json").exists()
    assert (run_dir / "trajectory.jsonl").exists()
    assert (run_dir / "patch.diff").read_text() == "diff --git a/file b/file\n"

    report_payload = json.loads((run_dir / "report.json").read_text())
    assert report_payload["run_id"] == run_id
    assert report_payload["status"] == "failed"
