"""Canonical identifier names shared across all agents."""

CANONICAL_KEYS: tuple[str, ...] = (
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
)

FOUNDATION_KEYS: tuple[str, ...] = (
    "experiment_id",
    "dataset_candidate_id",
)
