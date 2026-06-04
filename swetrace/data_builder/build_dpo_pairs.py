from swetrace.schema import RunReport


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


def _report_meta(report: RunReport) -> dict[str, str | bool]:
    return {
        "run_id": report.run_id,
        "task_id": report.task_id,
        "resolved": report.resolved,
        "patch_apply": report.patch_apply,
        "tests_passed": report.tests_passed,
        "status": report.status,
    }
