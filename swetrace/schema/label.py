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


class ReviewAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    task_id: str
    auto_primary_failure: str
    auto_severity: int = Field(ge=1, le=5)
    human_failure: str
    patch_quality: str
    sft_usable: bool
    dpo_usable: bool
    notes: str | None = None
    reviewer: str = "manual"
