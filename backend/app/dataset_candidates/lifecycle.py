from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.evaluations.lifecycle import register_evaluation_duckdb_views
from research_command_center_contract.enums import SourcePriority


@dataclass(frozen=True)
class RegisteredDatasetCandidate:
    dataset_candidate_id: int
    eval_failure_id: int
    source_eval_run_id: int
    source_model_version_id: int
    status: str


CANDIDATE_STATUSES = {"proposed", "approved", "rejected"}


def create_dataset_candidate(
    storage_root: Path,
    payload: dict[str, Any],
) -> RegisteredDatasetCandidate:
    eval_failure_id = int(payload["eval_failure_id"])
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_dataset_candidate_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)
    failure = _failure_context(duckdb_path=duckdb_path, eval_failure_id=eval_failure_id)
    if failure is None:
        raise ValueError(f"eval_failure_id {eval_failure_id} does not exist")

    dataset_candidate_id = int(
        payload.get("dataset_candidate_id")
        or _next_id(duckdb_path, "dataset_candidates", "dataset_candidate_id")
    )
    created_at = str(payload.get("created_at") or _utc_now())
    status = str(payload.get("status") or "proposed")
    if status not in CANDIDATE_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(CANDIDATE_STATUSES))}")
    row = {
        "dataset_candidate_id": dataset_candidate_id,
        "eval_failure_id": eval_failure_id,
        "source_eval_run_id": int(failure["eval_run_id"]),
        "source_eval_output_id": int(failure["eval_output_id"]),
        "source_model_version_id": int(failure["model_version_id"]),
        "program_id": int(failure.get("program_id") or 0),
        "experiment_id": int(failure.get("experiment_id") or 0),
        "target_dataset_id": int(payload.get("target_dataset_id") or 6),
        "failure_type": str(failure.get("failure_type") or "quality_gap"),
        "status": status,
        "proposed_input_text": str(payload.get("proposed_input_text") or failure.get("prompt_text") or ""),
        "proposed_target_text": str(payload.get("proposed_target_text") or ""),
        "review_notes": str(payload.get("review_notes") or ""),
        "source_priority": str(payload.get("source_priority") or SourcePriority.GENERATED_REAL.value),
        "created_at": created_at,
        "created_by_user_id": str(payload.get("created_by_user_id") or "user_demo_owner"),
        "reviewed_at": "",
        "reviewed_by_user_id": "",
        "included_dataset_id": 0,
        "included_dataset_version_id": 0,
        "included_at": "",
    }
    _write_parquet([row], _candidate_path(storage_root, dataset_candidate_id))
    _write_json(
        row,
        storage_root
        / "object_store"
        / "dataset_candidates"
        / f"dataset_candidate_id={dataset_candidate_id}"
        / "candidate_manifest.json",
    )
    register_dataset_candidate_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)
    return RegisteredDatasetCandidate(
        dataset_candidate_id=dataset_candidate_id,
        eval_failure_id=eval_failure_id,
        source_eval_run_id=row["source_eval_run_id"],
        source_model_version_id=row["source_model_version_id"],
        status=row["status"],
    )


def update_dataset_candidate(
    storage_root: Path,
    dataset_candidate_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    row = _read_candidate_row(storage_root, dataset_candidate_id)
    if row is None:
        raise ValueError(f"dataset_candidate_id {dataset_candidate_id} does not exist")

    if "status" in payload:
        status = str(payload["status"])
        if status not in CANDIDATE_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(CANDIDATE_STATUSES))}")
        row["status"] = status
    if "review_notes" in payload:
        row["review_notes"] = str(payload.get("review_notes") or "")
    if "reviewer_notes" in payload:
        row["review_notes"] = str(payload.get("reviewer_notes") or "")

    reviewed_by = payload.get("reviewed_by_user_id") or payload.get("reviewer_name") or payload.get("user_id")
    if reviewed_by:
        row["reviewed_by_user_id"] = str(reviewed_by)
    if "status" in payload or reviewed_by or "review_notes" in payload or "reviewer_notes" in payload:
        row["reviewed_at"] = str(payload.get("reviewed_at") or _utc_now())

    _write_candidate_row(storage_root, row)
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_dataset_candidate_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)
    return row


def mark_candidates_included(
    storage_root: Path,
    candidate_ids: list[int],
    dataset_id: int,
    dataset_version_id: int,
    included_at: str,
) -> None:
    for candidate_id in candidate_ids:
        row = _read_candidate_row(storage_root, candidate_id)
        if row is None:
            raise ValueError(f"dataset_candidate_id {candidate_id} does not exist")
        row["included_dataset_id"] = int(dataset_id)
        row["included_dataset_version_id"] = int(dataset_version_id)
        row["included_at"] = included_at
        _write_candidate_row(storage_root, row)
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_dataset_candidate_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)


def register_dataset_candidate_duckdb_view(storage_root: Path, duckdb_path: Path) -> None:
    register_evaluation_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    candidate_root = storage_root / "parquet" / "dataset_candidates"
    if not list(candidate_root.glob("**/*.parquet")):
        return
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(candidate_root / "**" / "*.parquet").replace("'", "''")
    connection = duckdb.connect(str(duckdb_path))
    try:
        connection.execute(
            f"""
            CREATE OR REPLACE VIEW dataset_candidates AS
            SELECT * FROM read_parquet('{pattern}', hive_partitioning = true, union_by_name = true)
            """
        )
    finally:
        connection.close()


def _failure_context(duckdb_path: Path, eval_failure_id: int) -> dict[str, Any] | None:
    if not duckdb_path.exists():
        return None
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            result = connection.execute(
                """
                SELECT
                    ef.*,
                    er.program_id,
                    er.experiment_id,
                    eo.prompt_text
                FROM eval_failures ef
                JOIN eval_runs er ON ef.eval_run_id = er.eval_run_id
                LEFT JOIN eval_outputs eo ON ef.eval_output_id = eo.eval_output_id
                WHERE ef.eval_failure_id = ?
                LIMIT 1
                """,
                [eval_failure_id],
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


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _read_candidate_row(storage_root: Path, dataset_candidate_id: int) -> dict[str, Any] | None:
    path = _candidate_path(storage_root, dataset_candidate_id)
    if not path.exists():
        return None
    row = pd.read_parquet(path).iloc[0].to_dict()
    return _candidate_row_with_defaults(row)


def _write_candidate_row(storage_root: Path, row: dict[str, Any]) -> None:
    row = _candidate_row_with_defaults(row)
    dataset_candidate_id = int(row["dataset_candidate_id"])
    _write_parquet([row], _candidate_path(storage_root, dataset_candidate_id))
    _write_json(
        row,
        storage_root
        / "object_store"
        / "dataset_candidates"
        / f"dataset_candidate_id={dataset_candidate_id}"
        / "candidate_manifest.json",
    )


def _candidate_row_with_defaults(row: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "source_priority": SourcePriority.GENERATED_REAL.value,
        "reviewed_at": "",
        "reviewed_by_user_id": "",
        "included_dataset_id": 0,
        "included_dataset_version_id": 0,
        "included_at": "",
    }
    hydrated = {**defaults, **row}
    for key in (
        "dataset_candidate_id",
        "eval_failure_id",
        "source_eval_run_id",
        "source_eval_output_id",
        "source_model_version_id",
        "program_id",
        "experiment_id",
        "target_dataset_id",
        "included_dataset_id",
        "included_dataset_version_id",
    ):
        hydrated[key] = int(hydrated.get(key) or 0)
    for key in (
        "failure_type",
        "status",
        "proposed_input_text",
        "proposed_target_text",
        "review_notes",
        "source_priority",
        "created_at",
        "created_by_user_id",
        "reviewed_at",
        "reviewed_by_user_id",
        "included_at",
    ):
        hydrated[key] = str(hydrated.get(key) or "")
    return hydrated


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _candidate_path(storage_root: Path, dataset_candidate_id: int) -> Path:
    return (
        storage_root
        / "parquet"
        / "dataset_candidates"
        / f"dataset_candidate_id={dataset_candidate_id}"
        / "candidate.parquet"
    )
