from swetrace.adapters.base import AgentAdapter, RunResult
from swetrace.artifacts import RunStore
from swetrace.schema import RunReport, TaskSpec, TrajectoryStep


class FakeAdapter(AgentAdapter):
    name = "fake"

    def run_task(self, task: TaskSpec, store: RunStore) -> RunResult:
        run_id = store.create_run(task, agent=self.name)
        steps = [
            TrajectoryStep(
                run_id=run_id,
                task_id=task.task_id,
                step_id=1,
                phase="plan",
                model_output="Inspect the issue and identify the likely failing function.",
            ),
            TrajectoryStep(
                run_id=run_id,
                task_id=task.task_id,
                step_id=2,
                phase="read",
                model_output="Read the expected target file.",
                tool_name="read_file",
                tool_args={"path": task.expected_files[0] if task.expected_files else "src/math_utils.py"},
                tool_result="def add_one(x): return x",
            ),
            TrajectoryStep(
                run_id=run_id,
                task_id=task.task_id,
                step_id=3,
                phase="edit",
                model_output="Apply the minimal off-by-one fix.",
                tool_name="edit_file",
                tool_args={"path": task.expected_files[0] if task.expected_files else "src/math_utils.py"},
                tool_result="patch applied",
                affected_files=task.expected_files or ["src/math_utils.py"],
                workspace_changed=True,
            ),
            TrajectoryStep(
                run_id=run_id,
                task_id=task.task_id,
                step_id=4,
                phase="test",
                model_output="Run the task test command and verify it passes.",
                tool_name="run_tests",
                tool_args={"command": task.test_command},
                tool_result="1 passed",
            ),
        ]
        patch = (
            "diff --git a/src/math_utils.py b/src/math_utils.py\n"
            "--- a/src/math_utils.py\n"
            "+++ b/src/math_utils.py\n"
            "@@\n"
            "-def add_one(x): return x\n"
            "+def add_one(x): return x + 1\n"
        )
        raw_log = "\n".join(f"[{step.phase}] {step.model_output}" for step in steps) + "\n"
        report = RunReport(
            run_id=run_id,
            task_id=task.task_id,
            agent=self.name,
            model="fake-model",
            status="resolved",
            patch_apply=True,
            tests_passed=True,
            resolved=True,
            num_steps=len(steps),
            num_tool_calls=sum(1 for step in steps if step.tool_name),
            num_edit_calls=sum(1 for step in steps if step.phase == "edit"),
            num_test_calls=sum(1 for step in steps if step.phase == "test"),
            stop_reason="final",
            final_patch_path="patch.diff",
            test_log_path="test.log",
        )

        store.write_text(run_id, "raw_agent.log", raw_log)
        store.write_trajectory(run_id, steps)
        store.write_text(run_id, "patch.diff", patch)
        store.write_text(run_id, "test.log", "fake test session\n1 passed\n")
        store.write_report(report)
        return RunResult(run_id=run_id, report=report, trajectory=steps)
