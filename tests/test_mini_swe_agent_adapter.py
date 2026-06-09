import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

from swetrace.adapters.mini_swe_agent import (
    MiniSweAgentAdapter,
    parse_mini_trajectory,
    render_command_template,
)
from swetrace.artifacts import RunStore
from swetrace.schema import TaskSpec

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parse_mini_trajectory_normalizes_messages_and_report() -> None:
    payload = json.loads(open("tests/fixtures/mini_swe_agent_success.traj.json").read())

    parsed = parse_mini_trajectory(
        payload=payload,
        run_id="run-1",
        task_id="fake-mini-task",
        agent="mini-swe-agent",
    )

    assert parsed.report.status == "resolved"
    assert parsed.report.patch_apply is True
    assert parsed.report.tests_passed is True
    assert parsed.report.num_steps == 5
    assert parsed.report.num_tool_calls == 2
    assert parsed.patch.startswith("diff --git")
    assert parsed.test_log == "1 passed"
    assert parsed.steps[1].tool_name == "str_replace_editor"
    assert parsed.steps[-1].phase == "test"


def test_parse_real_mini_trajectory_extracts_exit_patch_and_usage() -> None:
    payload = json.loads(open("tests/fixtures/mini_swe_agent_real_sqlfluff.traj.json").read())

    parsed = parse_mini_trajectory(
        payload=payload,
        run_id="run-1",
        task_id="sqlfluff__sqlfluff-1625",
        agent="mini-swe-agent",
    )

    assert parsed.report.model == "deepseek-v4-flash"
    assert parsed.report.token_usage.total > 0
    assert parsed.report.num_steps == 5
    assert parsed.report.num_tool_calls == 1
    assert parsed.patch.startswith("diff --git a/src/sqlfluff/rules/L031.py")
    assert parsed.steps[-1].phase == "final"


def test_parse_textbased_mini_trajectory_extracts_actions_and_patch() -> None:
    payload = {
        "info": {
            "config": {"model": {"model_name": "openai/qwen2.5-coder-7b-instruct"}},
        },
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "THOUGHT: Inspect the target file.\n\n"
                    "```mswea_bash_command\n"
                    "rg -n \"add_one\" src/math_utils.py\n"
                    "```"
                ),
                "extra": {
                    "actions": [{"command": 'rg -n "add_one" src/math_utils.py'}],
                    "response": {
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 5,
                            "total_tokens": 15,
                        }
                    },
                },
            },
            {
                "role": "user",
                "content": "<returncode>0</returncode>\n<output>1:def add_one(x): return x</output>",
                "extra": {
                    "raw_output": "1:def add_one(x): return x\n",
                    "returncode": 0,
                },
            },
            {
                "role": "assistant",
                "content": (
                    "THOUGHT: Submit the source patch.\n\n"
                    "```mswea_bash_command\n"
                    "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt\n"
                    "```"
                ),
                "extra": {
                    "actions": [{"command": "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt"}],
                    "response": {
                        "usage": {
                            "prompt_tokens": 20,
                            "completion_tokens": 6,
                            "total_tokens": 26,
                        }
                    },
                },
            },
            {
                "role": "exit",
                "content": "",
                "extra": {
                    "submission": (
                        "diff --git a/src/math_utils.py b/src/math_utils.py\n"
                        "--- a/src/math_utils.py\n"
                        "+++ b/src/math_utils.py\n"
                        "@@\n"
                        "-def add_one(x): return x\n"
                        "+def add_one(x): return x + 1\n"
                    )
                },
            },
        ],
    }

    parsed = parse_mini_trajectory(
        payload=payload,
        run_id="run-textbased",
        task_id="fake-mini-task",
        agent="mini-swe-agent",
    )

    assert parsed.report.model == "openai/qwen2.5-coder-7b-instruct"
    assert parsed.report.num_tool_calls == 2
    assert parsed.report.token_usage.total == 41
    assert parsed.patch.startswith("diff --git a/src/math_utils.py")
    assert parsed.steps[0].tool_name == "bash"
    assert parsed.steps[0].tool_args == {"command": 'rg -n "add_one" src/math_utils.py'}
    assert parsed.steps[0].phase == "search"
    assert parsed.steps[1].tool_result == "1:def add_one(x): return x\n"
    assert parsed.steps[-1].phase == "final"


def test_render_command_template_only_replaces_supported_placeholders() -> None:
    rendered = render_command_template(
        "runner --json '{\"keep\": true}' --instance {task_id} --output {traj_path}",
        {
            "task_id": "task-1",
            "traj_path": "/tmp/task-1.traj.json",
        },
    )

    assert "{\"keep\": true}" in rendered
    assert "{task_id}" not in rendered
    assert rendered.endswith("/tmp/task-1.traj.json")


def test_mini_adapter_runs_command_template_and_writes_artifacts(tmp_path) -> None:
    fixture = tmp_path / "fixture.traj.json"
    fixture.write_text(open("tests/fixtures/mini_swe_agent_success.traj.json").read())
    runner = tmp_path / "fake_mini_runner.py"
    runner.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import shutil
            import sys

            out = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
            out.mkdir(parents=True, exist_ok=True)
            shutil.copyfile({str(fixture)!r}, out / "fake-mini-task.traj.json")
            print("fake mini-swe-agent completed")
            """
        )
    )
    runner.chmod(runner.stat().st_mode | stat.S_IEXEC)
    task = TaskSpec(
        task_id="fake-mini-task",
        source="swebench_lite",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix add_one.",
        test_command="pytest tests/test_math.py",
    )
    store = RunStore(tmp_path / "runs")
    adapter = MiniSweAgentAdapter(
        command_template=f"{os.sys.executable} {runner} --instance {{task_id}} --output {{raw_dir}}"
    )

    result = adapter.run_task(task, store)

    run_dir = tmp_path / "runs" / result.run_id
    assert result.report.resolved is True
    assert (run_dir / "raw_agent.log").read_text().strip() == "fake mini-swe-agent completed"
    assert (run_dir / "raw_mini_swe_agent" / "fake-mini-task.traj.json").exists()
    assert (run_dir / "patch.diff").read_text().startswith("diff --git")
    assert (run_dir / "trajectory.jsonl").exists()


def test_mini_adapter_supports_traj_path_command_template(tmp_path) -> None:
    fixture = tmp_path / "fixture.traj.json"
    fixture.write_text(open("tests/fixtures/mini_swe_agent_success.traj.json").read())
    runner = tmp_path / "fake_mini_runner_file.py"
    runner.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import shutil
            import sys

            out = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile({str(fixture)!r}, out)
            """
        )
    )
    runner.chmod(runner.stat().st_mode | stat.S_IEXEC)
    task = TaskSpec(
        task_id="fake-mini-task",
        source="swebench_lite",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix add_one.",
        test_command="pytest tests/test_math.py",
    )
    store = RunStore(tmp_path / "runs")
    adapter = MiniSweAgentAdapter(
        command_template=f"{os.sys.executable} {runner} --instance {{task_id}} --output {{traj_path}}"
    )

    result = adapter.run_task(task, store)

    run_dir = tmp_path / "runs" / result.run_id
    assert result.report.resolved is True
    assert (run_dir / "raw_mini_swe_agent" / "fake-mini-task.traj.json").exists()


def test_mini_adapter_preserves_partial_trajectory_on_timeout(tmp_path) -> None:
    fixture = tmp_path / "fixture.traj.json"
    fixture.write_text(open("tests/fixtures/mini_swe_agent_success.traj.json").read())
    runner = tmp_path / "slow_mini_runner.py"
    runner.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import shutil
            import sys
            import time

            out = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile({str(fixture)!r}, out)
            print("wrote partial trajectory", flush=True)
            time.sleep(5)
            """
        )
    )
    runner.chmod(runner.stat().st_mode | stat.S_IEXEC)
    task = TaskSpec(
        task_id="fake-mini-task",
        source="swebench_lite",
        repo="owner/repo",
        base_commit="abc123",
        issue_text="Fix add_one.",
        test_command="pytest tests/test_math.py",
    )
    store = RunStore(tmp_path / "runs")
    adapter = MiniSweAgentAdapter(
        command_template=f"{os.sys.executable} {runner} --instance {{task_id}} --output {{traj_path}}",
        timeout_seconds=1,
    )

    result = adapter.run_task(task, store)

    run_dir = tmp_path / "runs" / result.run_id
    assert result.report.status == "stopped"
    assert result.report.stop_reason == "step_limit"
    assert result.report.num_steps == 5
    assert (run_dir / "trajectory.jsonl").read_text().count("\n") == 5
    assert "timed out after 1 seconds" in (run_dir / "raw_agent.log").read_text()


def test_run_task_cli_supports_mini_swe_agent_with_command_template(tmp_path) -> None:
    fixture = tmp_path / "fixture.traj.json"
    fixture.write_text(open("tests/fixtures/mini_swe_agent_success.traj.json").read())
    runner = tmp_path / "fake_mini_runner.py"
    runner.write_text(
        textwrap.dedent(
            f"""
            import pathlib
            import shutil
            import sys

            out = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
            out.mkdir(parents=True, exist_ok=True)
            shutil.copyfile({str(fixture)!r}, out / "fake-mini-task.traj.json")
            print("fake mini-swe-agent completed")
            """
        )
    )
    runner.chmod(runner.stat().st_mode | stat.S_IEXEC)
    task_path = tmp_path / "task.json"
    task_path.write_text(
        json.dumps(
            {
                "task_id": "fake-mini-task",
                "source": "swebench_lite",
                "repo": "owner/repo",
                "base_commit": "abc123",
                "issue_text": "Fix add_one.",
                "test_command": "pytest tests/test_math.py",
            }
        )
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.collect.run_task",
            "--task",
            str(task_path),
            "--agent",
            "mini-swe-agent",
            "--out",
            str(tmp_path / "runs"),
            "--command-template",
            f"{sys.executable} {runner} --instance {{task_id}} --output {{raw_dir}}",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["agent"] == "mini-swe-agent"
    assert payload["status"] == "resolved"


def test_recover_mini_runs_cli_rehydrates_existing_raw_trajectory(tmp_path) -> None:
    run_dir = tmp_path / "runs" / "existing-run"
    raw_dir = run_dir / "raw_mini_swe_agent"
    raw_dir.mkdir(parents=True)
    (run_dir / "task.json").write_text(
        json.dumps(
            {
                "task_id": "fake-mini-task",
                "source": "swebench_lite",
                "repo": "owner/repo",
                "base_commit": "abc123",
                "issue_text": "Fix add_one.",
                "test_command": "pytest tests/test_math.py",
            }
        )
    )
    (raw_dir / "fake-mini-task.traj.json").write_text(
        open("tests/fixtures/mini_swe_agent_success.traj.json").read()
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "swetrace.collect.recover_mini_runs",
            "--runs",
            str(tmp_path / "runs"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload == {"recovered_runs": 1, "skipped_runs": 0}
    assert json.loads((run_dir / "report.json").read_text())["run_id"] == "existing-run"
    assert (run_dir / "patch.diff").read_text().startswith("diff --git")
    assert (run_dir / "trajectory.jsonl").read_text().count("\n") == 5
