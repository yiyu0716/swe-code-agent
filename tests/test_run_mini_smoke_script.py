import json
import os
import subprocess
import textwrap
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_run_mini_smoke_uses_socksio_yolo_timeout_and_instance_metadata(tmp_path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir()

    uvx = bin_dir / "uvx"
    uvx.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' "$*" >> {calls_dir / "uvx_args.txt"}
            exit 0
            """
        )
    )
    uvx.chmod(0o755)

    fake_python = tmp_path / "python"
    fake_python.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            printf '%s\\n' "$*" > {calls_dir / "python_args.txt"}
            task=""
            while [[ $# -gt 0 ]]; do
              case "$1" in
                --task)
                  task="$2"
                  shift 2
                  ;;
                *)
                  shift
                  ;;
              esac
            done
            cp "$task" {calls_dir / "task.json"}
            """
        )
    )
    fake_python.chmod(0o755)

    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "SWETRACE_PYTHON": str(fake_python),
        "SWETRACE_MINI_INSTANCE": "sqlfluff__sqlfluff-1625",
        "SWETRACE_MINI_SUBSET": "/tmp/swebench_lite",
        "SWETRACE_MINI_MODEL": "deepseek/deepseek-chat",
        "SWETRACE_MINI_TIMEOUT_SECONDS": "17",
    }

    completed = subprocess.run(
        ["./scripts/run_mini_smoke.sh"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    python_args = (calls_dir / "python_args.txt").read_text()
    assert "--timeout-seconds 17" in python_args
    assert "--out /data/yiyuldx/swe/runs" in python_args
    assert "--instance sqlfluff__sqlfluff-1625" in python_args
    assert "--with socksio" in python_args
    assert "--yolo" in python_args
    assert "-c swebench.yaml" in python_args
    assert "-c environment.env.HTTP_PROXY=http://10.32.192.70:7890" in python_args
    assert "-c environment.env.HTTPS_PROXY=http://10.32.192.70:7890" in python_args
    assert "-c environment.env.http_proxy=http://10.32.192.70:7890" in python_args
    assert "-c environment.env.https_proxy=http://10.32.192.70:7890" in python_args
    assert "-c environment.env.PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple" in python_args
    assert "-c environment.env.PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn" in python_args
    assert "-c model.cost_tracking=ignore_errors" in python_args

    task = json.loads((calls_dir / "task.json").read_text())
    assert task["task_id"] == "sqlfluff__sqlfluff-1625"
    assert task["repo"] == "sqlfluff/sqlfluff"
    assert "real-agent-smoke" in task["tags"]


def test_data_scripts_default_to_data_directory() -> None:
    expected_fragments = {
        "scripts/run_fake.sh": 'OUT="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"',
        "scripts/run_fake_batch.sh": 'OUT="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"',
        "scripts/build_fake_data.sh": 'RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"',
        "scripts/auto_label_runs.sh": 'RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"',
        "scripts/download_swebench_lite.sh": 'OUT_DIR="${SWETRACE_SWEBENCH_CACHE:-/data/yiyuldx/swe/cache/swebench_lite}"',
        "scripts/select_swebench_tasks.sh": 'DATASET="${SWETRACE_SWEBENCH_SUBSET:-/data/yiyuldx/swe/cache/swebench_lite}"',
        "scripts/prepare_swebench_images.sh": 'TASKS="${SWETRACE_TASKS:-/data/yiyuldx/swe/outputs/tasks/swebench_lite_dev.jsonl}"',
        "scripts/build_review_queue.sh": '--runs "${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"',
        "scripts/serve_review_ui.sh": 'DPO_DATASET="${SWETRACE_DPO_DATASET:-/data/yiyuldx/swe/outputs/datasets/v0.1}"',
        "scripts/recover_mini_runs.sh": 'RUNS="${SWETRACE_RUNS:-/data/yiyuldx/swe/runs}"',
        "scripts/enrich_swebench_run_tasks.sh": 'DATASET="${SWETRACE_SWEBENCH_SUBSET:-/data/yiyuldx/swe/cache/swebench_lite}"',
    }

    for path, fragment in expected_fragments.items():
        assert fragment in (REPO_ROOT / path).read_text()
