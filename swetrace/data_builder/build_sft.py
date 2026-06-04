from swetrace.schema import TaskSpec, TrajectoryStep


def build_sft_plan(task: TaskSpec, steps: list[TrajectoryStep]) -> dict[str, str]:
    plan_steps = [step.model_output for step in steps if step.phase == "plan"]
    output = "\n".join(plan_steps) or "Inspect the issue, modify the minimal files, and run tests."
    return {
        "type": "sft_plan",
        "task_id": task.task_id,
        "instruction": "Given a software issue and repository context, write a concise repair plan.",
        "input": f"Issue:\n{task.issue_text}\n\nExpected files:\n{', '.join(task.expected_files)}",
        "output": output,
    }


def build_sft_patch(task: TaskSpec, patch: str) -> dict[str, str]:
    return {
        "type": "sft_patch",
        "task_id": task.task_id,
        "instruction": "Given a software issue, produce a minimal unified diff that fixes it.",
        "input": f"Issue:\n{task.issue_text}\n\nTest command:\n{task.test_command}",
        "output": patch,
    }


def build_sft_debug(task: TaskSpec, patch: str, test_log: str) -> dict[str, str]:
    return {
        "type": "sft_debug",
        "task_id": task.task_id,
        "instruction": "Given a patch and test log, diagnose the result and propose the next debugging step.",
        "input": f"Issue:\n{task.issue_text}\n\nPatch:\n{patch}\n\nTest log:\n{test_log}",
        "output": "The patch should be checked against the failing test and minimized to the relevant files.",
    }
