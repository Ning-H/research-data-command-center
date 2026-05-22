"""Shared enum values that must remain consistent across API, SDK, and pipelines."""

from enum import StrEnum


class SourcePriority(StrEnum):
    PUBLIC_REAL = "priority_1_public_real"
    PIPELINE_REAL = "priority_2_pipeline_real"
    CONSTRAINED_SYNTHETIC = "priority_3_constrained_synthetic"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
    KILLED = "killed"


class CheckpointStatus(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class ModelVersionStatus(StrEnum):
    CANDIDATE = "candidate"
    REGISTERED = "registered"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class EvalRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DatasetVersionStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
