from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Phase = Literal["plan", "search", "read", "edit", "test", "debug", "final"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TrajectoryStep(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    run_id: str
    task_id: str
    step_id: int
    phase: Phase
    model_output: str
    tool_name: str | None = None
    tool_args: dict[str, Any] = Field(default_factory=dict)
    tool_result: str | None = None
    affected_files: list[str] = Field(default_factory=list)
    workspace_changed: bool = False
    error: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
