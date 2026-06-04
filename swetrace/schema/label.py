from pydantic import BaseModel, ConfigDict, Field


class FailureLabel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    run_id: str
    primary_failure: str
    secondary_failures: list[str] = Field(default_factory=list)
    severity: int = Field(ge=1, le=5)
    is_data_usable_for_sft: bool
    is_data_usable_for_dpo: bool
    evidence: list[str] = Field(default_factory=list)
    reason: str | None = None
