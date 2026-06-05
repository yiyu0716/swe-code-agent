import json
import subprocess
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from swetrace.eval.swebench_official import (
    build_prediction_shards,
    import_run_statuses,
    official_image_for_instance,
    pip_proxy_dockerfile,
    parse_official_report,
    write_local_dataset_json,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_write_local_dataset_json_combines_parquet_splits(tmp_path) -> None:
    dataset = tmp_path / "cache" / "swebench_lite"
    data = dataset / "data"
    data.mkdir(parents=True)
    table = pa.table(
        {
            "repo": ["mwaskom/seaborn"],
            "instance_id": ["mwaskom__seaborn-3010"],
            "base_commit": ["abc123"],
            "patch": ["gold patch"],
            "test_patch": ["test patch"],
            "problem_statement": ["Fix missing values."],
            "hints_text": [""],
            "created_at": ["2024-01-01"],
            "version": ["0.12"],
            "FAIL_TO_PASS": ['["tests/test_stats.py::test_missing"]'],
            "PASS_TO_PASS": ['["tests/test_stats.py::test_existing"]'],
            "environment_setup_commit": ["def456"],
        }
    )
    pq.write_table(table, data / "dev-00000-of-00001.parquet")
    pq.write_table(table, data / "test-00000-of-00001.parquet")

    out = tmp_path / "dataset.json"
    payload = write_local_dataset_json(dataset, ["dev", "test"], out)

    assert payload == {"instances": 1, "out": str(out)}
    rows = json.loads(out.read_text())
    assert rows[0]["instance_id"] == "mwaskom__seaborn-3010"
    assert rows[0]["FAIL_TO_PASS"] == '["tests/test_stats.py::test_missing"]'


def test_build_prediction_shards_preserves_duplicate_instances(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(runs, "run-a", "sqlfluff__sqlfluff-1625", "patch a")
    _write_run(runs, "run-b", "sqlfluff__sqlfluff-1625", "patch b")
    _write_run(runs, "run-c", "mwaskom__seaborn-3010", "patch c")

    shards = build_prediction_shards(runs, model_prefix="swetrace-test")

    assert len(shards) == 2
    assert [row.run_id for row in shards[0].rows] == ["run-a", "run-c"]
    assert [row.run_id for row in shards[1].rows] == ["run-b"]
    assert shards[0].rows[0].prediction["model_name_or_path"] == "swetrace-test/run-a"
    assert shards[1].rows[0].prediction["model_patch"] == "patch b"


def test_official_eval_cli_writes_prediction_shards(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(runs, "run-a", "sqlfluff__sqlfluff-1625", "patch a")
    _write_run(runs, "run-b", "sqlfluff__sqlfluff-1625", "patch b")
    out = tmp_path / "predictions"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.eval.swebench_official",
            "write-predictions",
            "--runs",
            str(runs),
            "--out-dir",
            str(out),
            "--model-prefix",
            "swetrace-test",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["runs"] == 2
    assert payload["shards"] == 2
    assert (out / "shard_00.jsonl").exists()
    assert (out / "manifest.json").exists()


def test_official_eval_script_defaults_to_pip_proxy_images() -> None:
    script = REPO_ROOT / "scripts" / "run_official_eval.sh"

    assert 'INSTANCE_TAG="${SWETRACE_OFFICIAL_INSTANCE_TAG:-pip-proxy}"' in script.read_text()


def test_official_eval_cli_exposes_pip_proxy_image_command() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.eval.swebench_official",
            "--help",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "build-pip-proxy-image" in completed.stdout


def test_parse_official_report_extracts_run_level_status(tmp_path) -> None:
    log_root = tmp_path / "official_eval" / "logs" / "run_evaluation"
    report_dir = log_root / "official-1" / "swetrace-test__run-a" / "task-1"
    report_dir.mkdir(parents=True)
    (report_dir / "report.json").write_text(
        json.dumps(
            {
                "task-1": {
                    "patch_exists": True,
                    "patch_successfully_applied": True,
                    "resolved": True,
                    "tests_status": {
                        "FAIL_TO_PASS": {"success": ["test_new"], "failure": []},
                        "PASS_TO_PASS": {"success": ["test_old"], "failure": []},
                    },
                }
            }
        )
    )
    manifest = {
        "official_run_id": "official-1",
        "rows": [
            {
                "run_id": "run-a",
                "task_id": "task-1",
                "model_name_or_path": "swetrace-test/run-a",
                "prediction_path": "unused.jsonl",
                "shard": 0,
            }
        ],
    }

    rows = parse_official_report(tmp_path / "official_eval", manifest)

    assert rows == [
        {
            "run_id": "run-a",
            "task_id": "task-1",
            "official_run_id": "official-1",
            "completed": True,
            "patch_exists": True,
            "patch_successfully_applied": True,
            "resolved": True,
            "fail_to_pass_success": 1,
            "fail_to_pass_failure": 0,
            "pass_to_pass_success": 1,
            "pass_to_pass_failure": 0,
            "report_path": str(report_dir / "report.json"),
        }
    ]


def test_import_run_statuses_writes_official_eval_files(tmp_path) -> None:
    runs = tmp_path / "runs"
    _write_run(runs, "run-a", "task-1", "patch")
    statuses = tmp_path / "statuses.jsonl"
    statuses.write_text(
        json.dumps(
            {
                "run_id": "run-a",
                "task_id": "task-1",
                "official_run_id": "official-1",
                "completed": True,
                "patch_exists": True,
                "patch_successfully_applied": True,
                "resolved": True,
                "fail_to_pass_success": 1,
                "fail_to_pass_failure": 0,
                "pass_to_pass_success": 2,
                "pass_to_pass_failure": 0,
                "report_path": "/tmp/report.json",
            }
        )
        + "\n"
    )

    summary = import_run_statuses(statuses, runs)

    assert summary == {"rows": 1, "written": 1, "missing_runs": 0}
    payload = json.loads((runs / "run-a" / "official_eval.json").read_text())
    assert payload["source"] == "swebench_official"
    assert payload["resolved"] is True
    assert payload["tests_passed"] is True


def test_official_image_for_instance_supports_custom_tag_and_proxy_dockerfile() -> None:
    assert (
        official_image_for_instance("sqlfluff__sqlfluff-1625", tag="mirror-proxy")
        == "swebench/sweb.eval.x86_64.sqlfluff_1776_sqlfluff-1625:mirror-proxy"
    )

    dockerfile = pip_proxy_dockerfile(
        source_image="swebench/source:latest",
        http_proxy="http://10.32.192.70:7890",
        pip_index_url="https://pypi.tuna.tsinghua.edu.cn/simple",
        pip_trusted_host="pypi.tuna.tsinghua.edu.cn",
    )
    assert "proxy = http://10.32.192.70:7890" in dockerfile
    assert "ENV HTTP_PROXY" not in dockerfile


def _write_run(runs: Path, run_id: str, task_id: str, patch: str) -> None:
    run_dir = runs / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "source": "swebench_lite",
                "repo": "owner/repo",
                "base_commit": "abc123",
                "issue_text": "Fix issue.",
                "test_command": "mini-swe-agent managed evaluation",
            }
        )
    )
    (run_dir / "patch.diff").write_text(patch)
    (run_dir / "report.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "task_id": task_id,
                "agent": "mini-swe-agent",
                "status": "failed",
                "patch_apply": True,
                "tests_passed": False,
                "resolved": False,
            }
        )
    )
