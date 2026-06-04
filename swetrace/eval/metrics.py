from swetrace.schema import RunReport


def rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def summarize_reports(reports: list[RunReport]) -> dict[str, float | int]:
    num_runs = len(reports)
    total_steps = sum(report.num_steps for report in reports)
    total_tool_calls = sum(report.num_tool_calls for report in reports)
    return {
        "num_runs": num_runs,
        "resolved_rate": rate(sum(report.resolved for report in reports), num_runs),
        "patch_apply_rate": rate(sum(report.patch_apply for report in reports), num_runs),
        "test_pass_rate": rate(sum(report.tests_passed for report in reports), num_runs),
        "avg_steps": rate(total_steps, num_runs),
        "avg_tool_calls": rate(total_tool_calls, num_runs),
    }
