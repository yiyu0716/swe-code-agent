from swetrace.schema import RunReport, TaskSpec


def build_dpo_pairs(
    prompt: str,
    patches: dict[str, str],
    reports: list[RunReport],
) -> list[dict]:
    by_id = {report.run_id: report for report in reports}
    chosen_reports = [report for report in reports if report.resolved and report.tests_passed]
    rejected_reports = [
        report
        for report in reports
        if not report.resolved and report.status != "env_error" and report.patch_apply
    ]
    pairs = []
    for chosen in chosen_reports:
        for rejected in rejected_reports:
            if chosen.task_id != rejected.task_id:
                continue
            if chosen.run_id not in patches or rejected.run_id not in patches:
                continue
            pairs.append(
                {
                    "prompt": prompt,
                    "chosen": patches[chosen.run_id],
                    "rejected": patches[rejected.run_id],
                    "chosen_meta": _report_meta(by_id[chosen.run_id]),
                    "rejected_meta": _report_meta(by_id[rejected.run_id]),
                }
            )
    return pairs


def build_gold_dpo_pairs(
    tasks_by_run: dict[str, TaskSpec],
    patches: dict[str, str],
    reports: list[RunReport],
) -> list[dict]:
    pairs = []
    for report in reports:
        task = tasks_by_run.get(report.run_id)
        rejected_patch = patches.get(report.run_id, "")
        if task is None or not task.gold_patch or not rejected_patch.strip():
            continue
        if report.resolved or report.status == "env_error" or not report.patch_apply:
            continue
        pairs.append(
            {
                "prompt": _task_prompt(task),
                "chosen": task.gold_patch,
                "rejected": rejected_patch,
                "chosen_meta": {
                    "run_id": report.run_id,
                    "task_id": task.task_id,
                    "source": "swebench_gold_patch",
                    "resolved": True,
                    "patch_apply": True,
                    "tests_passed": True,
                    "status": "resolved",
                },
                "rejected_meta": _report_meta(report),
            }
        )
    return pairs


def _report_meta(report: RunReport) -> dict[str, str | bool]:
    return {
        "run_id": report.run_id,
        "task_id": report.task_id,
        "resolved": report.resolved,
        "patch_apply": report.patch_apply,
        "tests_passed": report.tests_passed,
        "status": report.status,
    }


def _task_prompt(task: TaskSpec) -> str:
    expected = ", ".join(task.expected_files)
    return (
        f"Issue:\n{task.issue_text}\n\n"
        f"Repository: {task.repo}\n"
        f"Base commit: {task.base_commit}\n"
        f"Expected files: {expected}\n"
        f"Test command: {task.test_command}"
    )
