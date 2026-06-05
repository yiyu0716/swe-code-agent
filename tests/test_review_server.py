import json
from pathlib import Path

import pytest

from swetrace.labeling.review_server import (
    build_review_payload,
    load_run_detail,
    save_annotation,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n")


def test_build_review_payload_marks_annotated_items(tmp_path) -> None:
    queue = tmp_path / "manual_review_queue.jsonl"
    queue.write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "task_id": "task-1",
                "status": "failed",
                "primary_failure": "PatchError.IncompleteFix",
                "severity": 3,
                "is_data_usable_for_sft": False,
                "is_data_usable_for_dpo": True,
            }
        )
        + "\n"
    )
    annotations = tmp_path / "manual_annotations.jsonl"
    annotations.write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "task_id": "task-1",
                "auto_primary_failure": "PatchError.IncompleteFix",
                "auto_severity": 3,
                "human_failure": "PatchError.IncompleteFix",
                "patch_quality": "close",
                "sft_usable": False,
                "dpo_usable": True,
                "notes": "Already reviewed.",
                "reviewer": "manual",
            }
        )
        + "\n"
    )

    payload = build_review_payload(queue=queue, annotations=annotations)

    assert payload["total"] == 1
    assert payload["annotated"] == 1
    assert payload["items"][0]["is_annotated"] is True
    assert payload["items"][0]["annotation"]["patch_quality"] == "close"


def test_load_run_detail_returns_artifact_text(tmp_path) -> None:
    run_dir = tmp_path / "runs" / "run-1"
    _write_json(
        run_dir / "task.json",
        {
            "task_id": "task-1",
            "source": "swebench_lite",
            "repo": "owner/repo",
            "base_commit": "abc123",
            "issue_text": "Fix the parser.",
            "test_command": "pytest",
            "gold_patch": "gold patch",
        },
    )
    _write_json(
        run_dir / "report.json",
        {
            "run_id": "run-1",
            "task_id": "task-1",
            "agent": "mini-swe-agent",
            "status": "failed",
            "patch_apply": True,
            "tests_passed": False,
            "resolved": False,
        },
    )
    _write_json(
        run_dir / "labels.json",
        {
            "task_id": "task-1",
            "run_id": "run-1",
            "primary_failure": "PatchError.IncompleteFix",
            "secondary_failures": ["TestError.UnitTestFail"],
            "severity": 3,
            "is_data_usable_for_sft": False,
            "is_data_usable_for_dpo": True,
        },
    )
    (run_dir / "patch.diff").write_text("agent patch")
    (run_dir / "test.log").write_text("1 failed")

    detail = load_run_detail(runs=tmp_path / "runs", run_id="run-1")

    assert detail["run_id"] == "run-1"
    assert detail["task"]["issue_text"] == "Fix the parser."
    assert detail["task"]["gold_patch"] == "gold patch"
    assert detail["patch"] == "agent patch"
    assert detail["test_log"] == "1 failed"
    assert detail["label"]["primary_failure"] == "PatchError.IncompleteFix"


def test_save_annotation_upserts_and_rejects_unknown_run(tmp_path) -> None:
    queue = tmp_path / "manual_review_queue.jsonl"
    queue.write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "task_id": "task-1",
                "primary_failure": "PatchError.IncompleteFix",
                "severity": 3,
            }
        )
        + "\n"
    )
    out = tmp_path / "manual_annotations.jsonl"

    result = save_annotation(
        queue=queue,
        out=out,
        payload={
            "run_id": "run-1",
            "human_failure": "PatchError.IncompleteFix",
            "patch_quality": "partial",
            "sft_usable": False,
            "dpo_usable": True,
            "notes": "First pass.",
        },
    )
    assert result == {"annotations": 1, "updated": "run-1", "out": str(out)}

    result = save_annotation(
        queue=queue,
        out=out,
        payload={
            "run_id": "run-1",
            "human_failure": "PatchError.IncompleteFix",
            "patch_quality": "close",
            "sft_usable": False,
            "dpo_usable": True,
            "notes": "Updated.",
        },
    )
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert result["annotations"] == 1
    assert len(rows) == 1
    assert rows[0]["patch_quality"] == "close"
    assert rows[0]["notes"] == "Updated."

    with pytest.raises(ValueError, match="run_id not found"):
        save_annotation(
            queue=queue,
            out=out,
            payload={
                "run_id": "missing-run",
                "human_failure": "PatchError.IncompleteFix",
                "patch_quality": "poor",
                "sft_usable": False,
                "dpo_usable": False,
            },
        )
