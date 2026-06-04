import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swetrace.adapters.base import AgentAdapter, RunResult
from swetrace.artifacts import RunStore
from swetrace.schema import RunReport, TaskSpec, TokenUsage, TrajectoryStep


@dataclass(frozen=True)
class ParsedMiniTrajectory:
    steps: list[TrajectoryStep]
    report: RunReport
    patch: str
    test_log: str


class MiniSweAgentAdapter(AgentAdapter):
    name = "mini-swe-agent"

    def __init__(self, command_template: str | None = None, timeout_seconds: int = 1800) -> None:
        self.command_template = command_template or os.environ.get(
            "SWETRACE_MINI_SWE_COMMAND",
            "mini-extra swebench-single --instance {task_id} --output {traj_path} --exit-immediately",
        )
        self.timeout_seconds = timeout_seconds

    def run_task(self, task: TaskSpec, store: RunStore) -> RunResult:
        run_id = store.create_run(task, agent=self.name)
        run_dir = store.run_dir(run_id)
        raw_dir = run_dir / "raw_mini_swe_agent"
        raw_dir.mkdir(parents=True, exist_ok=True)
        command = render_command_template(
            self.command_template,
            {
                "task_id": task.task_id,
                "raw_dir": str(raw_dir),
                "traj_path": str(raw_dir / f"{task.task_id}.traj.json"),
                "issue_text": shlex.quote(task.issue_text),
                "repo": task.repo,
                "test_command": shlex.quote(task.test_command),
            },
        )

        completed = subprocess.run(
            shlex.split(command),
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        raw_log = _join_logs(completed.stdout, completed.stderr)
        store.write_text(run_id, "raw_agent.log", raw_log)

        trajectory_path = find_trajectory_file(raw_dir, task.task_id)
        if trajectory_path is None:
            report = RunReport(
                run_id=run_id,
                task_id=task.task_id,
                agent=self.name,
                status="env_error",
                patch_apply=False,
                tests_passed=False,
                resolved=False,
                stop_reason="env_error",
            )
            store.write_trajectory(run_id, [])
            store.write_text(run_id, "patch.diff", "")
            store.write_text(run_id, "test.log", raw_log)
            store.write_report(report)
            return RunResult(run_id=run_id, report=report, trajectory=[])

        payload = json.loads(trajectory_path.read_text())
        parsed = parse_mini_trajectory(payload, run_id=run_id, task_id=task.task_id, agent=self.name)
        store.write_trajectory(run_id, parsed.steps)
        store.write_text(run_id, "patch.diff", parsed.patch)
        store.write_text(run_id, "test.log", parsed.test_log)
        store.write_report(parsed.report)
        return RunResult(run_id=run_id, report=parsed.report, trajectory=parsed.steps)


def parse_mini_trajectory(
    payload: dict[str, Any],
    run_id: str,
    task_id: str,
    agent: str,
) -> ParsedMiniTrajectory:
    messages = payload.get("messages") or payload.get("trajectory") or []
    info = payload.get("info") or {}
    patch = _first_text(
        info,
        ["submission", "patch", "diff", "final_patch"],
    ) or _exit_submission(messages)
    test_log = _first_text(info, ["test_output", "test_log", "tests", "evaluation_log"])
    steps = [
        _message_to_step(message, run_id=run_id, task_id=task_id, step_id=index)
        for index, message in enumerate(messages, start=1)
    ]
    if not test_log:
        test_log = _last_tool_result(steps)

    patch_apply = bool(patch.strip())
    tests_passed = _tests_passed(test_log)
    status = "resolved" if patch_apply and tests_passed else "failed"
    report = RunReport(
        run_id=run_id,
        task_id=task_id,
        agent=agent,
        model=_model_name(payload=payload, info=info, messages=messages),
        status=status,
        patch_apply=patch_apply,
        tests_passed=tests_passed,
        resolved=status == "resolved",
        num_steps=len(steps),
        num_tool_calls=sum(1 for step in steps if step.tool_name),
        num_edit_calls=sum(1 for step in steps if step.phase == "edit"),
        num_test_calls=sum(1 for step in steps if step.phase == "test"),
        token_usage=_token_usage(messages),
        stop_reason="final",
        final_patch_path="patch.diff",
        test_log_path="test.log",
    )
    return ParsedMiniTrajectory(steps=steps, report=report, patch=patch, test_log=test_log)


def find_trajectory_file(raw_dir: Path, task_id: str) -> Path | None:
    candidates = sorted(raw_dir.rglob("*.traj.json")) + sorted(raw_dir.rglob("*traj*.json"))
    exact = [path for path in candidates if task_id in path.name]
    if exact:
        return exact[0]
    if candidates:
        return candidates[0]
    return None


def render_command_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _message_to_step(message: dict[str, Any], run_id: str, task_id: str, step_id: int) -> TrajectoryStep:
    content = str(message.get("content") or "")
    tool_name = None
    tool_args: dict[str, Any] = {}
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        function = tool_calls[0].get("function") or {}
        tool_name = str(function.get("name") or "")
        args = function.get("arguments") or {}
        if isinstance(args, str):
            try:
                tool_args = json.loads(args)
            except json.JSONDecodeError:
                tool_args = {"raw": args}
        elif isinstance(args, dict):
            tool_args = args
    phase = _infer_phase(content=content, tool_name=tool_name, tool_args=tool_args, role=message.get("role"))
    return TrajectoryStep(
        run_id=run_id,
        task_id=task_id,
        step_id=step_id,
        phase=phase,
        model_output=content,
        tool_name=tool_name,
        tool_args=tool_args,
        tool_result=content if message.get("role") == "tool" else None,
        affected_files=_affected_files(tool_args),
        workspace_changed=phase == "edit",
    )


def _infer_phase(
    content: str,
    tool_name: str | None,
    tool_args: dict[str, Any],
    role: str | None,
):
    haystack = f"{content} {tool_name or ''} {json.dumps(tool_args, ensure_ascii=False)}".lower()
    if role == "exit":
        return "final"
    if role == "tool" and ("passed" in haystack or "failed" in haystack or "pytest" in haystack):
        return "test"
    if any(word in haystack for word in ["pytest", "test", "1 passed", "failed"]):
        return "test"
    if any(word in haystack for word in ["edit", "str_replace", "replace", "write"]):
        return "edit"
    if any(word in haystack for word in ["view", "read", "cat", "inspect"]):
        return "read"
    if any(word in haystack for word in ["grep", "search", "find"]):
        return "search"
    return "plan"


def _affected_files(tool_args: dict[str, Any]) -> list[str]:
    paths = []
    for key in ("path", "file", "filename"):
        value = tool_args.get(key)
        if isinstance(value, str):
            paths.append(value)
    return paths


def _first_text(payload: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def _exit_submission(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") != "exit":
            continue
        extra = message.get("extra") or {}
        submission = extra.get("submission")
        if isinstance(submission, str):
            return submission
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def _model_name(payload: dict[str, Any], info: dict[str, Any], messages: list[dict[str, Any]]) -> str:
    for value in (payload.get("model"), info.get("model")):
        if value:
            return str(value)
    for message in messages:
        response = (message.get("extra") or {}).get("response") or {}
        model = response.get("model")
        if model:
            return str(model)
    config_model = ((info.get("config") or {}).get("model") or {}).get("model_name")
    return str(config_model or "")


def _token_usage(messages: list[dict[str, Any]]) -> TokenUsage:
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    for message in messages:
        usage = ((message.get("extra") or {}).get("response") or {}).get("usage") or {}
        input_tokens += int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens += int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens += int(usage.get("total_tokens") or 0)
    if not total_tokens:
        total_tokens = input_tokens + output_tokens
    return TokenUsage(input=input_tokens, output=output_tokens, total=total_tokens)


def _last_tool_result(steps: list[TrajectoryStep]) -> str:
    for step in reversed(steps):
        if step.tool_result:
            return step.tool_result
    return ""


def _tests_passed(test_log: str) -> bool:
    lowered = test_log.lower()
    return "passed" in lowered and "failed" not in lowered and "error" not in lowered


def _join_logs(stdout: str, stderr: str) -> str:
    parts = []
    if stdout:
        parts.append(stdout)
    if stderr:
        parts.append(stderr)
    return "\n".join(part.rstrip("\n") for part in parts if part).rstrip("\n") + ("\n" if parts else "")
