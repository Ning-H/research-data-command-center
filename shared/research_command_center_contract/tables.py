"""Minimum shared table contracts.

These definitions are intentionally compact. Agent checkpoints can propose
amendments before implementation when a shared field is needed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TableContract:
    name: str
    storage_layer: str
    columns: tuple[str, ...]
    primary_entity_id: str | None = None
    is_time_series: bool = False


APP_METADATA_TABLES: tuple[TableContract, ...] = (
    TableContract(
        name="experiments",
        storage_layer="postgres",
        columns=("experiment_id", "name", "description", "created_at", "created_by_user_id"),
        primary_entity_id="experiment_id",
    ),
    TableContract(
        name="dataset_versions",
        storage_layer="postgres",
        columns=(
            "dataset_id",
            "dataset_version_id",
            "name",
            "version",
            "status",
            "source_priority",
            "raw_uri",
            "parquet_uri",
            "schema_uri",
            "parent_dataset_version_id",
            "created_at",
            "created_by_user_id",
        ),
        primary_entity_id="dataset_version_id",
    ),
    TableContract(
        name="run_configs",
        storage_layer="postgres",
        columns=("run_config_id", "dataset_version_id", "model_id", "config_uri", "created_at"),
        primary_entity_id="run_config_id",
    ),
    TableContract(
        name="training_runs",
        storage_layer="postgres",
        columns=(
            "run_id",
            "experiment_id",
            "run_config_id",
            "dataset_version_id",
            "status",
            "started_at",
            "ended_at",
            "created_by_user_id",
        ),
        primary_entity_id="run_id",
    ),
    TableContract(
        name="checkpoints",
        storage_layer="postgres",
        columns=(
            "checkpoint_id",
            "run_id",
            "dataset_version_id",
            "step",
            "status",
            "artifact_uri",
            "created_at",
        ),
        primary_entity_id="checkpoint_id",
    ),
    TableContract(
        name="model_versions",
        storage_layer="postgres",
        columns=(
            "model_id",
            "model_version_id",
            "checkpoint_id",
            "run_id",
            "dataset_version_id",
            "status",
            "artifact_uri",
            "created_at",
            "created_by_user_id",
        ),
        primary_entity_id="model_version_id",
    ),
    TableContract(
        name="eval_suites",
        storage_layer="postgres",
        columns=("eval_suite_id", "name", "version", "status", "case_source_uri", "created_at"),
        primary_entity_id="eval_suite_id",
    ),
    TableContract(
        name="eval_runs",
        storage_layer="postgres",
        columns=(
            "eval_run_id",
            "eval_suite_id",
            "model_version_id",
            "run_id",
            "checkpoint_id",
            "dataset_version_id",
            "status",
            "started_at",
            "ended_at",
        ),
        primary_entity_id="eval_run_id",
    ),
    TableContract(
        name="eval_failures",
        storage_layer="postgres",
        columns=(
            "eval_failure_id",
            "eval_run_id",
            "eval_output_id",
            "eval_case_id",
            "model_version_id",
            "dataset_version_id",
            "severity",
            "failure_type",
            "created_at",
        ),
        primary_entity_id="eval_failure_id",
    ),
    TableContract(
        name="dataset_candidates",
        storage_layer="postgres",
        columns=(
            "dataset_candidate_id",
            "eval_failure_id",
            "source_eval_run_id",
            "source_model_version_id",
            "target_dataset_id",
            "status",
            "created_at",
            "created_by_user_id",
        ),
        primary_entity_id="dataset_candidate_id",
    ),
)

ANALYTICAL_TABLES: tuple[TableContract, ...] = (
    TableContract(
        name="training_metrics",
        storage_layer="parquet_duckdb",
        columns=("run_id", "timestamp", "step", "metric_name", "metric_value"),
        primary_entity_id="run_id",
        is_time_series=True,
    ),
    TableContract(
        name="compute_metrics",
        storage_layer="parquet_duckdb",
        columns=("run_id", "node_id", "gpu_id", "timestamp", "step", "metric_name", "metric_value"),
        primary_entity_id="run_id",
        is_time_series=True,
    ),
    TableContract(
        name="eval_outputs",
        storage_layer="parquet_duckdb",
        columns=(
            "eval_output_id",
            "eval_run_id",
            "eval_case_id",
            "model_version_id",
            "dataset_version_id",
            "output_text",
            "score",
            "scoring_method",
            "created_at",
        ),
        primary_entity_id="eval_run_id",
    ),
    TableContract(
        name="dataset_quality_reports",
        storage_layer="parquet_duckdb",
        columns=("dataset_version_id", "timestamp", "metric_name", "metric_value", "source_priority"),
        primary_entity_id="dataset_version_id",
        is_time_series=True,
    ),
    TableContract(
        name="dataset_usage",
        storage_layer="parquet_duckdb",
        columns=(
            "dataset_version_id",
            "run_id",
            "model_version_id",
            "eval_run_id",
            "usage_type",
            "created_at",
        ),
        primary_entity_id="dataset_version_id",
    ),
)


def table_by_name(name: str) -> TableContract:
    for table in (*APP_METADATA_TABLES, *ANALYTICAL_TABLES):
        if table.name == name:
            return table
    raise KeyError(f"Unknown shared table contract: {name}")
