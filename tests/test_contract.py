from research_command_center_contract import (
    ANALYTICAL_TABLES,
    APP_METADATA_TABLES,
    CANONICAL_KEYS,
    RunStatus,
    SourcePriority,
)


def test_required_canonical_keys_are_present() -> None:
    required = {
        "dataset_id",
        "dataset_version_id",
        "run_id",
        "run_config_id",
        "checkpoint_id",
        "model_id",
        "model_version_id",
        "node_id",
        "gpu_id",
        "eval_suite_id",
        "eval_run_id",
        "eval_case_id",
        "eval_output_id",
        "eval_failure_id",
        "regression_id",
        "user_id",
    }

    assert set(CANONICAL_KEYS) == required


def test_run_status_values_match_contract() -> None:
    assert {status.value for status in RunStatus} == {
        "queued",
        "running",
        "failed",
        "completed",
        "killed",
    }


def test_source_priority_values_match_project_guidelines() -> None:
    assert {priority.value for priority in SourcePriority} == {
        "PUBLIC_REAL",
        "GENERATED_REAL",
        "SYNTHETIC_REALISTIC",
    }


def test_metrics_tables_are_long_format() -> None:
    tables = {table.name: table for table in ANALYTICAL_TABLES}

    for table_name in ("training_metrics", "compute_metrics"):
        columns = set(tables[table_name].columns)
        assert {"timestamp", "step", "metric_name", "metric_value"}.issubset(columns)
        assert tables[table_name].is_time_series


def test_core_lineage_tables_keep_foreign_keys_explicit() -> None:
    tables = {table.name: table for table in (*APP_METADATA_TABLES, *ANALYTICAL_TABLES)}

    assert {"run_id", "dataset_version_id"}.issubset(tables["checkpoints"].columns)
    assert {"checkpoint_id", "run_id", "dataset_version_id"}.issubset(
        tables["model_versions"].columns
    )
    assert {"eval_run_id", "model_version_id", "dataset_version_id"}.issubset(
        tables["eval_outputs"].columns
    )
