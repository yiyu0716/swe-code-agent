from swetrace.schema import FailureLabel, RunReport


def label_run(report: RunReport, raw_log: str = "") -> FailureLabel:
    lowered = raw_log.lower()
    if report.status == "env_error":
        primary = _environment_failure(lowered)
        return FailureLabel(
            task_id=report.task_id,
            run_id=report.run_id,
            primary_failure=primary,
            secondary_failures=[],
            severity=1,
            is_data_usable_for_sft=False,
            is_data_usable_for_dpo=False,
            evidence=[_clip(raw_log)] if raw_log else [],
            reason="Environment/setup failure; excluded from model-failure training data.",
        )

    if not report.patch_apply:
        return FailureLabel(
            task_id=report.task_id,
            run_id=report.run_id,
            primary_failure="PatchError.PatchApplyFail",
            secondary_failures=[],
            severity=2,
            is_data_usable_for_sft=False,
            is_data_usable_for_dpo=True,
            evidence=[_clip(raw_log)] if raw_log else [],
            reason="Patch did not apply, but can be useful as a rejected preference sample.",
        )

    if report.patch_apply and not report.tests_passed:
        return FailureLabel(
            task_id=report.task_id,
            run_id=report.run_id,
            primary_failure="PatchError.IncompleteFix",
            secondary_failures=["TestError.UnitTestFail"],
            severity=3,
            is_data_usable_for_sft=False,
            is_data_usable_for_dpo=True,
            evidence=[_clip(raw_log)] if raw_log else [],
            reason="Patch applied but tests did not pass.",
        )

    return FailureLabel(
        task_id=report.task_id,
        run_id=report.run_id,
        primary_failure="",
        secondary_failures=[],
        severity=1,
        is_data_usable_for_sft=True,
        is_data_usable_for_dpo=False,
        evidence=[],
        reason="Resolved run; no failure label assigned.",
    )


def _environment_failure(lowered_raw_log: str) -> str:
    if any(token in lowered_raw_log for token in ["hugging face", "load_dataset", "dataset"]):
        return "EnvironmentError.DatasetLoadFail"
    if any(token in lowered_raw_log for token in ["docker", "container"]):
        return "EnvironmentError.DockerFail"
    if any(token in lowered_raw_log for token in ["dependency", "pip", "install"]):
        return "EnvironmentError.DependencyInstallFail"
    return "EnvironmentError.RepoSetupFail"


def _clip(text: str, limit: int = 500) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
