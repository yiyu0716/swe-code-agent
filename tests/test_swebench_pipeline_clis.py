import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from swetrace.schema import TaskSpec

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_select_swebench_tasks_exports_tasks_jsonl(tmp_path) -> None:
    cache = tmp_path / "cache" / "swebench_lite" / "data"
    cache.mkdir(parents=True)
    parquet_path = cache / "dev-00000-of-00001.parquet"
    table = pa.table(
        {
            "repo": ["sqlfluff/sqlfluff", "pydicom/pydicom"],
            "instance_id": ["sqlfluff__sqlfluff-1625", "pydicom__pydicom-901"],
            "base_commit": ["abc123", "def456"],
            "patch": [
                "diff --git a/src/rule.py b/src/rule.py\n+++ b/src/rule.py\n",
                "diff --git a/pydicom/file.py b/pydicom/file.py\n+++ b/pydicom/file.py\n",
            ],
            "problem_statement": ["Fix sqlfluff rule.", "Fix pydicom parser."],
            "version": ["0.6", "1.3"],
        }
    )
    pq.write_table(table, parquet_path)
    out = tmp_path / "tasks.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.collect.select_swebench_tasks",
            "--dataset",
            str(tmp_path / "cache" / "swebench_lite"),
            "--split",
            "dev",
            "--repo",
            "sqlfluff/sqlfluff",
            "--limit",
            "1",
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["selected_tasks"] == 1
    rows = [TaskSpec.model_validate_json(line) for line in out.read_text().splitlines()]
    assert [row.task_id for row in rows] == ["sqlfluff__sqlfluff-1625"]
    assert rows[0].repo == "sqlfluff/sqlfluff"
    assert rows[0].expected_files == ["src/rule.py"]
    assert "swebench-lite" in rows[0].tags


def test_prepare_swebench_images_dry_run_writes_manifest(tmp_path) -> None:
    tasks_path = tmp_path / "tasks.jsonl"
    tasks_path.write_text(
        json.dumps(
            {
                "task_id": "sqlfluff__sqlfluff-1625",
                "source": "swebench_lite",
                "repo": "sqlfluff/sqlfluff",
                "base_commit": "abc123",
                "issue_text": "Fix issue.",
                "test_command": "mini-swe-agent managed evaluation",
            }
        )
        + "\n"
    )
    manifest = tmp_path / "images.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.collect.prepare_swebench_images",
            "--tasks",
            str(tasks_path),
            "--out",
            str(manifest),
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == {"planned": 1, "pulled": 0, "failed": 0, "out": str(manifest)}
    rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    assert rows == [
        {
            "task_id": "sqlfluff__sqlfluff-1625",
            "image": "docker.io/swebench/sweb.eval.x86_64.sqlfluff_1776_sqlfluff-1625:latest",
            "status": "planned",
            "returncode": None,
            "log_preview": "",
        }
    ]


def test_review_queue_exports_non_resolved_runs(tmp_path) -> None:
    run_dir = tmp_path / "runs" / "run-1"
    run_dir.mkdir(parents=True)
    (run_dir / "report.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "task_id": "task-1",
                "agent": "mini-swe-agent",
                "status": "failed",
                "patch_apply": True,
                "tests_passed": False,
                "resolved": False,
                "num_steps": 12,
                "num_tool_calls": 7,
            }
        )
    )
    (run_dir / "labels.json").write_text(
        json.dumps(
            {
                "task_id": "task-1",
                "run_id": "run-1",
                "primary_failure": "PatchError.IncompleteFix",
                "secondary_failures": ["TestError.UnitTestFail"],
                "severity": 3,
                "is_data_usable_for_sft": False,
                "is_data_usable_for_dpo": True,
                "evidence": ["tests failed"],
                "reason": "Patch applied but tests did not pass.",
            }
        )
    )
    (run_dir / "patch.diff").write_text("diff --git a/file.py b/file.py\n+bad patch\n")
    (run_dir / "test.log").write_text("1 failed\n")
    out = tmp_path / "manual_review_queue.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.labeling.review_queue",
            "--runs",
            str(tmp_path / "runs"),
            "--out",
            str(out),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == {"review_items": 1, "out": str(out)}
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert rows[0]["run_id"] == "run-1"
    assert rows[0]["primary_failure"] == "PatchError.IncompleteFix"
    assert rows[0]["needs_human_review"] is True
    assert rows[0]["patch_preview"].startswith("diff --git")
