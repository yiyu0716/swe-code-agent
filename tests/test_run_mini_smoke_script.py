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
    assert "--instance sqlfluff__sqlfluff-1625" in python_args
    assert "--with socksio" in python_args
    assert "--yolo" in python_args

    task = json.loads((calls_dir / "task.json").read_text())
    assert task["task_id"] == "sqlfluff__sqlfluff-1625"
    assert task["repo"] == "sqlfluff/sqlfluff"
    assert "real-agent-smoke" in task["tags"]
