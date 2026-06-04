from swetrace.labeling.rule_labeler import label_run
from swetrace.schema import RunReport


def test_rule_labeler_detects_dataset_download_env_error() -> None:
    report = RunReport(
        run_id="run-1",
        task_id="task-1",
        agent="mini-swe-agent",
        status="env_error",
        patch_apply=False,
        tests_passed=False,
        resolved=False,
    )
    label = label_run(
        report,
        raw_log="Couldn't find 'princeton-nlp/SWE-Bench_Lite' on the Hugging Face Hub",
    )

    assert label.primary_failure == "EnvironmentError.DatasetLoadFail"
    assert label.severity == 1
    assert label.is_data_usable_for_sft is False
    assert label.is_data_usable_for_dpo is False


def test_rule_labeler_detects_patch_apply_failure() -> None:
    report = RunReport(
        run_id="run-2",
        task_id="task-2",
        agent="mini-swe-agent",
        status="failed",
        patch_apply=False,
        tests_passed=False,
        resolved=False,
    )

    label = label_run(report, raw_log="patch failed to apply")

    assert label.primary_failure == "PatchError.PatchApplyFail"
    assert label.is_data_usable_for_dpo is True
