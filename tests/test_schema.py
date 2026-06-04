from swetrace.schema import (
    FailureLabel,
    RunReport,
    TaskSpec,
    TrajectoryStep,
)


def test_task_spec_round_trips_json() -> None:
    task = TaskSpec(
        task_id="task-1",
        source="fake",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix the failing parser.",
        test_command="pytest tests/test_parser.py",
        expected_files=["parser.py"],
        tags=["bugfix"],
    )

    restored = TaskSpec.model_validate_json(task.model_dump_json())

    assert restored.task_id == "task-1"
    assert restored.expected_files == ["parser.py"]
    assert restored.tags == ["bugfix"]


def test_trajectory_step_records_tool_and_file_effects() -> None:
    step = TrajectoryStep(
        run_id="run-1",
        task_id="task-1",
        step_id=2,
        phase="edit",
        model_output="Patch add_one.",
        tool_name="edit_file",
        tool_args={"path": "src/math_utils.py"},
        tool_result="ok",
        affected_files=["src/math_utils.py"],
        workspace_changed=True,
    )

    payload = step.model_dump(mode="json")

    assert payload["phase"] == "edit"
    assert payload["tool_args"]["path"] == "src/math_utils.py"
    assert payload["workspace_changed"] is True


def test_report_and_failure_label_have_project_metrics() -> None:
    report = RunReport(
        run_id="run-1",
        task_id="task-1",
        agent="fake",
        model="fake-model",
        status="resolved",
        patch_apply=True,
        tests_passed=True,
        resolved=True,
        num_steps=4,
        num_tool_calls=3,
        num_edit_calls=1,
        num_test_calls=1,
        stop_reason="final",
    )
    label = FailureLabel(
        task_id="task-1",
        run_id="run-1",
        primary_failure="PatchError.IncompleteFix",
        secondary_failures=["ContextError.MissingTestContext"],
        severity=3,
        is_data_usable_for_sft=False,
        is_data_usable_for_dpo=True,
        evidence=["test log still fails"],
    )

    assert report.resolved is True
    assert report.token_usage.total == 0
    assert label.severity == 3
    assert label.is_data_usable_for_dpo is True
