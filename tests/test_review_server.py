import json
from pathlib import Path
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import ProxyHandler, build_opener
from urllib.error import HTTPError

import pytest

from swetrace.labeling.review_server import (
    build_review_payload,
    _make_handler,
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


def test_review_server_serves_static_report_pages_safely(tmp_path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "annotation_calibration.html").write_text("<h1>标注校准页</h1>")
    (reports / "data_quality_report.html").write_text("<h1>数据质量报告</h1>")
    handler = _make_handler(
        reports=reports,
        runs=tmp_path / "runs",
        queue=tmp_path / "queue.jsonl",
        annotations=tmp_path / "annotations.jsonl",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(f"{base}/annotation_calibration.html", timeout=3) as response:
            assert response.status == HTTPStatus.OK
            assert "标注校准页" in response.read().decode()
        with opener.open(f"{base}/data_quality_report.html", timeout=3) as response:
            assert response.status == HTTPStatus.OK
            assert "数据质量报告" in response.read().decode()
        with pytest.raises(HTTPError) as excinfo:
            opener.open(f"{base}/../secret.html", timeout=3)
        assert excinfo.value.code == HTTPStatus.NOT_FOUND
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
