from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvalCasePayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    eval_case_id: int | None = None
    case_name: str | None = None
    prompt_text: str | None = None
    prompt: str | None = None
    expected_topics: list[str] = Field(default_factory=list)
    required_sections: list[str] = Field(default_factory=list)
    rubric: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class EvalSuiteCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_suite_id: int | None = None
    program_id: int | None = None
    experiment_id: int | None = None
    name: str | None = None
    eval_suite_name: str | None = None
    version: str = "v1"
    status: str = "active"
    case_source_uri: str | None = None
    source_priority: str | None = None
    created_at: str | None = None
    created_by_user_id: str = "user_demo_owner"
    cases: list[EvalCasePayload] = Field(default_factory=list)

    @field_validator("name", "eval_suite_name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class EvalFailurePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_failure_id: int | None = None
    failure_type: str = "quality_gap"
    severity: str = "medium"
    failure_reason: str = ""
    evidence_text: str = ""
    status: str = "open"
    created_at: str | None = None


class EvalOutputPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_output_id: int | None = None
    eval_case_id: int
    prompt_text: str = ""
    output_text: str = ""
    score: float | None = None
    scoring_method: str | None = None
    scores: dict[str, float] = Field(default_factory=dict)
    failures: list[EvalFailurePayload] = Field(default_factory=list)

    @field_validator("scores")
    @classmethod
    def require_scores(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("scores must contain at least one metric")
        return value


class EvalRunCreatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eval_run_id: int | None = None
    eval_suite_id: int
    program_id: int | None = None
    experiment_id: int | None = None
    model_version_id: int
    status: str = "completed"
    source_priority: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    created_by_user_id: str = "user_demo_owner"
    scoring_method: str | None = None
    evaluator_name: str = ""
    evaluator_version: str = ""
    eval_job_uri: str = ""
    external_eval_run_id: str = ""
    git_commit: str = ""
    environment: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    outputs: list[EvalOutputPayload]

    @field_validator("outputs")
    @classmethod
    def require_outputs(cls, value: list[EvalOutputPayload]) -> list[EvalOutputPayload]:
        if not value:
            raise ValueError("outputs must contain at least one eval output")
        return value

