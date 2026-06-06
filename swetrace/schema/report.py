from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["resolved", "failed", "stopped", "env_error"]
StopReason = Literal["final", "step_limit", "retry_limit", "tool_error", "env_error"]
LabelSource = Literal["mini_swe_agent", "swebench_official"]


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: int = 0
    output: int = 0
    total: int = 0


class RunReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    task_id: str
    agent: str
    model: str | None = None
    status: RunStatus
    patch_apply: bool
    tests_passed: bool
    resolved: bool
    num_steps: int = 0
    num_tool_calls: int = 0
    num_edit_calls: int = 0
    num_test_calls: int = 0
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    stop_reason: StopReason = "final"
    final_patch_path: str | None = None
    test_log_path: str | None = None
    label_source: LabelSource = "mini_swe_agent"
    legacy_status: RunStatus | None = None
    legacy_patch_apply: bool | None = None
    legacy_tests_passed: bool | None = None
    legacy_resolved: bool | None = None
    official_run_id: str | None = None
    official_completed: bool | None = None
    official_patch_exists: bool | None = None
    official_patch_successfully_applied: bool | None = None
    official_fail_to_pass_success: int | None = None
    official_fail_to_pass_failure: int | None = None
    official_pass_to_pass_success: int | None = None
    official_pass_to_pass_failure: int | None = None
    official_report_path: str | None = None
