from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


PROGRAM_STATUSES = {"planning", "active", "paused", "completed", "archived"}

JSON_LIST_FIELDS = {
    "researcher_names",
    "success_metrics",
    "tags",
    "linked_dataset_ids",
    "linked_experiment_ids",
}

STRING_FIELDS = {
    "program_name",
    "short_name",
    "program_description",
    "problem_statement",
    "origin_story",
    "research_goal",
    "hypothesis",
    "target_outcome",
    "status",
    "research_area",
    "current_focus",
    "owner_name",
    "decision_notes",
    "input_source",
    "created_by_user_id",
    "updated_by_user_id",
}


@dataclass(frozen=True)
class RegisteredResearchProgram:
    program_id: int
    program_name: str
    status: str
    researcher_names: list[str]
    created_at: str
    updated_at: str


def register_research_program(storage_root: Path, payload: dict[str, Any]) -> RegisteredResearchProgram:
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_research_program_duckdb_view(
        storage_root=storage_root,
        duckdb_path=duckdb_path,
        replace_existing=True,
    )
    program_id = int(payload.get("program_id") or _next_id(duckdb_path, "research_programs", "program_id"))
    if _program_path(storage_root, program_id).exists():
        raise ValueError(f"program_id {program_id} already exists")

    created_at = payload.get("created_at") or _utc_now()
    row = _normalize_program_row(
        {
            **payload,
            "program_id": program_id,
            "created_at": created_at,
            "updated_at": payload.get("updated_at") or created_at,
            "created_by_user_id": payload.get("created_by_user_id")
            or payload.get("owner_name")
            or "user_demo_owner",
            "updated_by_user_id": payload.get("updated_by_user_id")
            or payload.get("created_by_user_id")
            or payload.get("owner_name")
            or "user_demo_owner",
        }
    )
    _write_parquet([row], _program_path(storage_root, program_id))
    _write_json(row, _program_manifest_path(storage_root, program_id))
    register_research_program_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)
    return RegisteredResearchProgram(
        program_id=program_id,
        program_name=row["program_name"],
        status=row["status"],
        researcher_names=json.loads(row["researcher_names_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def update_research_program(
    storage_root: Path,
    program_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    path = _program_path(storage_root, program_id)
    frame = _read_parquet_if_exists(path)
    if frame.empty:
        raise ValueError(f"program_id {program_id} does not exist")
    current = frame.iloc[0].to_dict()
    mutable_fields = STRING_FIELDS | JSON_LIST_FIELDS
    updates = {key: value for key, value in payload.items() if key in mutable_fields}
    if not updates:
        raise ValueError("payload must include at least one updateable research program field")
    updated = _normalize_program_row(
        {
            **current,
            **updates,
            "program_id": program_id,
            "created_at": current["created_at"],
            "updated_at": payload.get("updated_at") or _utc_now(),
            "created_by_user_id": current["created_by_user_id"],
            "updated_by_user_id": payload.get("updated_by_user_id")
            or payload.get("owner_name")
            or current.get("updated_by_user_id")
            or current.get("created_by_user_id")
            or "user_demo_owner",
        }
    )
    _write_parquet([updated], path)
    _write_json(updated, _program_manifest_path(storage_root, program_id))
    register_research_program_duckdb_view(
        storage_root=storage_root,
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
        replace_existing=True,
    )
    return updated


def register_research_program_duckdb_view(
    storage_root: Path,
    duckdb_path: Path,
    replace_existing: bool = False,
) -> None:
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    program_root = storage_root / "parquet" / "research_programs"
    if not list(program_root.glob("**/*.parquet")):
        return
    if not replace_existing and _duckdb_has_table(duckdb_path, "research_programs"):
        return
    pattern = str(program_root / "**" / "*.parquet").replace("'", "''")
    create_clause = "CREATE OR REPLACE VIEW" if replace_existing else "CREATE VIEW"
    connection = duckdb.connect(str(duckdb_path))
    try:
        try:
            connection.execute(
                f"""
                {create_clause} research_programs AS
                SELECT * FROM read_parquet('{pattern}', hive_partitioning = true, union_by_name = true)
                """
            )
        except duckdb.TransactionException:
            # Another API request created the same view concurrently.
            return
    finally:
        connection.close()


def _normalize_program_row(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "planning")
    if status not in PROGRAM_STATUSES:
        allowed = ", ".join(sorted(PROGRAM_STATUSES))
        raise ValueError(f"status must be one of: {allowed}")
    program_name = str(payload.get("program_name") or "").strip()
    if not program_name:
        raise ValueError("program_name is required")
    researcher_names = _string_list(payload, "researcher_names")
    success_metrics = _string_list(payload, "success_metrics")
    tags = _string_list(payload, "tags")
    linked_dataset_ids = [int(value) for value in _list_value(payload, "linked_dataset_ids")]
    linked_experiment_ids = [int(value) for value in _list_value(payload, "linked_experiment_ids")]
    return {
        "program_id": int(payload["program_id"]),
        "program_name": program_name,
        "short_name": str(payload.get("short_name") or program_name).strip(),
        "program_description": str(payload.get("program_description") or "").strip(),
        "problem_statement": str(payload.get("problem_statement") or "").strip(),
        "origin_story": str(payload.get("origin_story") or "").strip(),
        "research_goal": str(payload.get("research_goal") or "").strip(),
        "hypothesis": str(payload.get("hypothesis") or "").strip(),
        "target_outcome": str(payload.get("target_outcome") or "").strip(),
        "status": status,
        "research_area": str(payload.get("research_area") or "").strip(),
        "current_focus": str(payload.get("current_focus") or "").strip(),
        "owner_name": str(payload.get("owner_name") or "").strip(),
        "researcher_names_json": json.dumps(researcher_names, sort_keys=True),
        "success_metrics_json": json.dumps(success_metrics, sort_keys=True),
        "tags_json": json.dumps(tags, sort_keys=True),
        "linked_dataset_ids_json": json.dumps(linked_dataset_ids, sort_keys=True),
        "linked_experiment_ids_json": json.dumps(linked_experiment_ids, sort_keys=True),
        "decision_notes": str(payload.get("decision_notes") or "").strip(),
        "input_source": str(payload.get("input_source") or "ui").strip(),
        "created_at": str(payload["created_at"]),
        "updated_at": str(payload["updated_at"]),
        "created_by_user_id": str(payload.get("created_by_user_id") or "user_demo_owner"),
        "updated_by_user_id": str(payload.get("updated_by_user_id") or "user_demo_owner"),
    }


def _string_list(payload: dict[str, Any], key: str) -> list[str]:
    return [str(value).strip() for value in _list_value(payload, key) if str(value).strip()]


def _list_value(payload: dict[str, Any], key: str) -> list[Any]:
    raw_value = payload.get(key)
    if raw_value is None:
        json_value = payload.get(f"{key}_json")
        if isinstance(json_value, str) and json_value:
            return list(json.loads(json_value))
        return []
    if isinstance(raw_value, str):
        return [value.strip() for value in raw_value.split(",") if value.strip()]
    return list(raw_value)


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


def _duckdb_has_table(duckdb_path: Path, table_name: str) -> bool:
    if not duckdb_path.exists():
        return False
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            connection.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
        except duckdb.Error:
            return False
        return True
    finally:
        connection.close()


def _program_path(storage_root: Path, program_id: int) -> Path:
    return (
        storage_root
        / "parquet"
        / "research_programs"
        / f"program_id={program_id}"
        / "research_program.parquet"
    )


def _program_manifest_path(storage_root: Path, program_id: int) -> Path:
    return (
        storage_root
        / "object_store"
        / "research_programs"
        / f"program_id={program_id}"
        / "registration_manifest.json"
    )


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _read_parquet_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
