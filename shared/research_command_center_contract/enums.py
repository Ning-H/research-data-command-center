"""Shared enum values that must remain consistent across API, SDK, and pipelines."""

from enum import StrEnum


class SourcePriority(StrEnum):
    PUBLIC_REAL = "PUBLIC_REAL"
    GENERATED_REAL = "GENERATED_REAL"
    SYNTHETIC_REALISTIC = "SYNTHETIC_REALISTIC"


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
