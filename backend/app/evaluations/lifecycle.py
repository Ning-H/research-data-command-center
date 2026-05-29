from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.models.lifecycle import register_model_duckdb_views
from research_command_center_contract.enums import EvalRunStatus, SourcePriority


@dataclass(frozen=True)
class RegisteredEvalSuite:
    eval_suite_id: int
    case_count: int
    status: str


@dataclass(frozen=True)
class RegisteredEvalRun:
    eval_run_id: int
    eval_suite_id: int
    model_version_id: int
    output_count: int
    failure_count: int
    status: str


def register_eval_suite(storage_root: Path, payload: dict[str, Any]) -> RegisteredEvalSuite:
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_evaluation_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    eval_suite_id = int(payload.get("eval_suite_id") or _next_id(duckdb_path, "eval_suites", "eval_suite_id"))
    if _eval_suite_path(storage_root, eval_suite_id).exists():
        raise ValueError(f"eval_suite_id {eval_suite_id} already exists")

    created_at = str(payload.get("created_at") or _utc_now())
    cases = list(payload.get("cases") or [])
    case_source_uri = str(
        payload.get("case_source_uri")
        or storage_root / "object_store" / "eval_suites" / f"eval_suite_id={eval_suite_id}" / "cases.json"
    )
    suite_row = {
        "eval_suite_id": eval_suite_id,
        "program_id": _optional_int(payload.get("program_id")),
        "experiment_id": _optional_int(payload.get("experiment_id")),
        "name": str(payload.get("name") or payload.get("eval_suite_name") or "").strip(),
        "version": str(payload.get("version") or "v1").strip(),
        "status": str(payload.get("status") or "active").strip(),
        "case_source_uri": case_source_uri,
        "source_priority": str(payload.get("source_priority") or SourcePriority.GENERATED_REAL.value),
        "created_at": created_at,
        "created_by_user_id": str(payload.get("created_by_user_id") or "user_demo_owner"),
    }
    if not suite_row["name"]:
        raise ValueError("eval suite name is required")

    case_rows: list[dict[str, Any]] = []
    next_case_id = _next_id(duckdb_path, "eval_cases", "eval_case_id")
    for offset, case in enumerate(cases):
        eval_case_id = int(case.get("eval_case_id") or next_case_id + offset)
        case_rows.append(
            {
                "eval_case_id": eval_case_id,
                "eval_suite_id": eval_suite_id,
                "case_name": str(case.get("case_name") or f"case-{eval_case_id}").strip(),
                "prompt_text": str(case.get("prompt_text") or case.get("prompt") or "").strip(),
                "expected_topics_json": json.dumps(_string_list(case.get("expected_topics")), sort_keys=True),
                "required_sections_json": json.dumps(_string_list(case.get("required_sections")), sort_keys=True),
                "rubric_json": json.dumps(case.get("rubric") or {}, sort_keys=True),
                "tags_json": json.dumps(_string_list(case.get("tags")), sort_keys=True),
                "created_at": created_at,
            }
        )
    _write_parquet([suite_row], _eval_suite_path(storage_root, eval_suite_id))
    if case_rows:
        _write_parquet(case_rows, _eval_cases_path(storage_root, eval_suite_id))

    _write_json(
        {"eval_suite": suite_row, "cases": case_rows},
        storage_root / "object_store" / "eval_suites" / f"eval_suite_id={eval_suite_id}" / "suite_manifest.json",
    )
    _write_json(
        {"cases": cases},
        storage_root / "object_store" / "eval_suites" / f"eval_suite_id={eval_suite_id}" / "cases.json",
    )
    register_evaluation_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    return RegisteredEvalSuite(
        eval_suite_id=eval_suite_id,
        case_count=len(case_rows),
        status=suite_row["status"],
    )


def register_eval_run(storage_root: Path, payload: dict[str, Any]) -> RegisteredEvalRun:
    eval_suite_id = int(payload["eval_suite_id"])
    model_version_id = int(payload["model_version_id"])
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_evaluation_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    model = _model_context(duckdb_path=duckdb_path, model_version_id=model_version_id)
    if model is None:
        raise ValueError(f"model_version_id {model_version_id} does not exist")
    if not _suite_exists(duckdb_path=duckdb_path, eval_suite_id=eval_suite_id):
        raise ValueError(f"eval_suite_id {eval_suite_id} does not exist")

    eval_run_id = int(payload.get("eval_run_id") or _next_id(duckdb_path, "eval_runs", "eval_run_id"))
    started_at = str(payload.get("started_at") or _utc_now())
    ended_at = str(payload.get("ended_at") or started_at)
    status = str(payload.get("status") or EvalRunStatus.COMPLETED.value)
    outputs = list(payload.get("outputs") or [])
    if not outputs:
        raise ValueError("outputs must contain at least one eval output")

    eval_run_row = {
        "eval_run_id": eval_run_id,
        "eval_suite_id": eval_suite_id,
        "program_id": int(payload.get("program_id") or model.get("program_id") or 0),
        "experiment_id": int(payload.get("experiment_id") or model.get("experiment_id") or 0),
        "model_version_id": model_version_id,
        "run_id": int(model["run_id"]),
        "checkpoint_id": int(model["checkpoint_id"]),
        "dataset_id": int(model["dataset_id"]),
        "dataset_version_id": int(model["dataset_version_id"]),
        "status": status,
        "source_priority": str(payload.get("source_priority") or SourcePriority.GENERATED_REAL.value),
        "started_at": started_at,
        "ended_at": ended_at,
        "created_by_user_id": str(payload.get("created_by_user_id") or "user_demo_owner"),
    }

    output_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    failure_rows: list[dict[str, Any]] = []
    next_output_id = _next_id(duckdb_path, "eval_outputs", "eval_output_id")
    next_failure_id = _next_id(duckdb_path, "eval_failures", "eval_failure_id")
    for output_offset, output in enumerate(outputs):
        eval_output_id = int(output.get("eval_output_id") or next_output_id + output_offset)
        eval_case_id = int(output["eval_case_id"])
        scores = {str(k): float(v) for k, v in (output.get("scores") or {}).items()}
        overall_score = float(output.get("score") or scores.get("overall") or _mean(scores.values()))
        scoring_method = str(output.get("scoring_method") or payload.get("scoring_method") or "rubric_v1")
        output_rows.append(
            {
                "eval_output_id": eval_output_id,
                "eval_run_id": eval_run_id,
                "eval_case_id": eval_case_id,
                "model_version_id": model_version_id,
                "dataset_id": int(model["dataset_id"]),
                "dataset_version_id": int(model["dataset_version_id"]),
                "prompt_text": str(output.get("prompt_text") or ""),
                "output_text": str(output.get("output_text") or ""),
                "score": overall_score,
                "scoring_method": scoring_method,
                "scores_json": json.dumps(scores, sort_keys=True),
                "created_at": ended_at,
            }
        )
        for metric_name, metric_value in scores.items():
            score_rows.append(
                {
                    "eval_run_id": eval_run_id,
                    "eval_output_id": eval_output_id,
                    "eval_case_id": eval_case_id,
                    "model_version_id": model_version_id,
                    "metric_name": metric_name,
                    "metric_value": float(metric_value),
                    "scoring_method": scoring_method,
                    "created_at": ended_at,
                }
            )
        for failure_offset, failure in enumerate(output.get("failures") or []):
            failure_rows.append(
                {
                    "eval_failure_id": int(failure.get("eval_failure_id") or next_failure_id + len(failure_rows)),
                    "eval_run_id": eval_run_id,
                    "eval_output_id": eval_output_id,
                    "eval_case_id": eval_case_id,
                    "model_version_id": model_version_id,
                    "dataset_id": int(model["dataset_id"]),
                    "dataset_version_id": int(model["dataset_version_id"]),
                    "failure_type": str(failure.get("failure_type") or "quality_gap"),
                    "severity": str(failure.get("severity") or "medium"),
                    "failure_reason": str(failure.get("failure_reason") or ""),
                    "evidence_text": str(failure.get("evidence_text") or ""),
                    "status": str(failure.get("status") or "open"),
                    "created_at": str(failure.get("created_at") or ended_at),
                }
            )

    _write_parquet([eval_run_row], _eval_run_path(storage_root, eval_run_id))
    _write_parquet(output_rows, _eval_outputs_path(storage_root, eval_run_id))
    _write_parquet(score_rows, _eval_scores_path(storage_root, eval_run_id))
    if failure_rows:
        _write_parquet(failure_rows, _eval_failures_path(storage_root, eval_run_id))
    _write_json(
        {"eval_run": eval_run_row, "outputs": output_rows, "failures": failure_rows},
        storage_root / "object_store" / "eval_runs" / f"eval_run_id={eval_run_id}" / "eval_run_manifest.json",
    )
    register_evaluation_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    return RegisteredEvalRun(
        eval_run_id=eval_run_id,
        eval_suite_id=eval_suite_id,
        model_version_id=model_version_id,
        output_count=len(output_rows),
        failure_count=len(failure_rows),
        status=status,
    )


def register_evaluation_duckdb_views(storage_root: Path, duckdb_path: Path) -> None:
    register_model_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    view_patterns = {
        "eval_suites": storage_root / "parquet" / "eval_suites" / "**" / "*.parquet",
        "eval_cases": storage_root / "parquet" / "eval_cases" / "**" / "*.parquet",
        "eval_runs": storage_root / "parquet" / "eval_runs" / "**" / "*.parquet",
        "eval_outputs": storage_root / "parquet" / "eval_outputs" / "**" / "*.parquet",
        "eval_scores": storage_root / "parquet" / "eval_scores" / "**" / "*.parquet",
        "eval_failures": storage_root / "parquet" / "eval_failures" / "**" / "*.parquet",
    }
    connection = duckdb.connect(str(duckdb_path))
    try:
        for view_name, pattern in view_patterns.items():
            root = pattern.parents[1]
            if not list(root.glob("**/*.parquet")):
                continue
            escaped_pattern = str(pattern).replace("'", "''")
            connection.execute(
                f"""
                CREATE OR REPLACE VIEW {view_name} AS
                SELECT * FROM read_parquet('{escaped_pattern}', hive_partitioning = true, union_by_name = true)
                """
            )
    finally:
        connection.close()


def _model_context(duckdb_path: Path, model_version_id: int) -> dict[str, Any] | None:
    if not duckdb_path.exists():
        return None
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            result = connection.execute(
                "SELECT * FROM model_versions WHERE model_version_id = ? LIMIT 1",
                [model_version_id],
            )
        except duckdb.Error:
            return None
        row = result.fetchone()
        if row is None:
            return None
        columns = [column[0] for column in result.description]
        return dict(zip(columns, row, strict=True))
    finally:
        connection.close()


def _suite_exists(duckdb_path: Path, eval_suite_id: int) -> bool:
    if not duckdb_path.exists():
        return False
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            row = connection.execute(
                "SELECT 1 FROM eval_suites WHERE eval_suite_id = ? LIMIT 1",
                [eval_suite_id],
            ).fetchone()
        except duckdb.Error:
            return False
        return row is not None
    finally:
        connection.close()


def _next_id(duckdb_path: Path, table_name: str, column_name: str) -> int:
    if not duckdb_path.exists():
        return 1
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            value = connection.execute(f"SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}").fetchone()[0]
        except duckdb.Error:
            value = 0
        return int(value or 0) + 1
    finally:
        connection.close()


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in list(value) if str(item).strip()]


def _mean(values: Any) -> float:
    value_list = list(values)
    if not value_list:
        return 0.0
    return sum(float(value) for value in value_list) / len(value_list)


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _eval_suite_path(storage_root: Path, eval_suite_id: int) -> Path:
    return storage_root / "parquet" / "eval_suites" / f"eval_suite_id={eval_suite_id}" / "suite.parquet"


def _eval_cases_path(storage_root: Path, eval_suite_id: int) -> Path:
    return storage_root / "parquet" / "eval_cases" / f"eval_suite_id={eval_suite_id}" / "cases.parquet"


def _eval_run_path(storage_root: Path, eval_run_id: int) -> Path:
    return storage_root / "parquet" / "eval_runs" / f"eval_run_id={eval_run_id}" / "eval_run.parquet"


def _eval_outputs_path(storage_root: Path, eval_run_id: int) -> Path:
    return storage_root / "parquet" / "eval_outputs" / f"eval_run_id={eval_run_id}" / "outputs.parquet"


def _eval_scores_path(storage_root: Path, eval_run_id: int) -> Path:
    return storage_root / "parquet" / "eval_scores" / f"eval_run_id={eval_run_id}" / "scores.parquet"


def _eval_failures_path(storage_root: Path, eval_run_id: int) -> Path:
    return storage_root / "parquet" / "eval_failures" / f"eval_run_id={eval_run_id}" / "failures.parquet"
