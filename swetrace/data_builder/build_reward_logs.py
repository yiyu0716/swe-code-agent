from swetrace.schema import RunReport


def build_reward_logs(report: RunReport) -> dict[str, float | str | bool]:
    reward = 0.0
    if report.patch_apply:
        reward += 0.3
    else:
        reward -= 0.2
    if report.tests_passed:
        reward += 0.7
    if report.resolved:
        reward += 0.3
    if report.status == "env_error":
        reward -= 0.4
    if report.num_tool_calls > 15:
        reward -= 0.1 * (report.num_tool_calls - 15)

    return {
        "type": "reward_log",
        "run_id": report.run_id,
        "task_id": report.task_id,
        "reward": round(reward, 3),
        "patch_apply": report.patch_apply,
        "tests_passed": report.tests_passed,
        "resolved": report.resolved,
        "status": report.status,
    }
