from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    source: str
    repo: str
    base_commit: str
    issue_text: str
    test_command: str
    expected_files: list[str] = Field(default_factory=list)
    gold_patch: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    tags: list[str] = Field(default_factory=list)
