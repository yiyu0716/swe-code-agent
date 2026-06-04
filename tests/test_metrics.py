from swetrace.eval.metrics import summarize_reports
from swetrace.schema import RunReport


def test_summarize_reports_computes_rates() -> None:
    reports = [
        RunReport(
            run_id="run-1",
            task_id="task-1",
            agent="fake",
            status="resolved",
            patch_apply=True,
            tests_passed=True,
            resolved=True,
            num_steps=4,
            num_tool_calls=3,
        ),
        RunReport(
            run_id="run-2",
            task_id="task-2",
            agent="fake",
            status="failed",
            patch_apply=True,
            tests_passed=False,
            resolved=False,
            num_steps=6,
            num_tool_calls=5,
        ),
    ]

    summary = summarize_reports(reports)

    assert summary["num_runs"] == 2
    assert summary["resolved_rate"] == 0.5
    assert summary["patch_apply_rate"] == 1.0
    assert summary["test_pass_rate"] == 0.5
    assert summary["avg_steps"] == 5.0
