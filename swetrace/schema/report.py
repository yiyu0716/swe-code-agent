from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["resolved", "failed", "stopped", "env_error"]
StopReason = Literal["final", "step_limit", "retry_limit", "tool_error", "env_error"]


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
