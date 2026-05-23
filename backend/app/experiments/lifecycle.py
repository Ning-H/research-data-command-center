from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.research_programs.lifecycle import attach_research_program_links, research_program_exists


EXPERIMENT_STATUSES = {"planning", "active", "paused", "completed", "archived"}

JSON_LIST_FIELDS = {
    "tags",
    "variants",
    "notes",
    "linked_datasets",
    "linked_run_ids",
    "linked_model_version_ids",
}

STRING_FIELDS = {
    "experiment_name",
    "experiment_description",
    "research_question",
    "hypothesis",
    "experiment_type",
    "status",
    "owner_name",
    "evaluation_plan",
    "decision_notes",
    "input_source",
    "created_by_user_id",
    "updated_by_user_id",
}


@dataclass(frozen=True)
class RegisteredExperiment:
    experiment_id: int
    program_id: int
    experiment_name: str
    status: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ExperimentNoteResult:
    experiment_id: int
    note_id: int
    notes: list[dict[str, Any]]
    updated_at: str


def experiment_exists(storage_root: Path, experiment_id: int) -> bool:
    return _experiment_path(storage_root, experiment_id).exists()


def get_experiment_program_id(storage_root: Path, experiment_id: int) -> int | None:
    frame = _read_parquet_if_exists(_experiment_path(storage_root, experiment_id))
    if frame.empty:
        return None
    return int(frame.iloc[0]["program_id"])


def register_experiment(storage_root: Path, payload: dict[str, Any]) -> RegisteredExperiment:
    program_id = int(payload["program_id"])
    if not research_program_exists(storage_root, program_id):
        raise ValueError(f"program_id {program_id} does not exist")

    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_experiment_duckdb_view(
        storage_root=storage_root,
        duckdb_path=duckdb_path,
        replace_existing=True,
    )
    experiment_id = int(payload.get("experiment_id") or _next_id(duckdb_path))
    if experiment_exists(storage_root, experiment_id):
        raise ValueError(f"experiment_id {experiment_id} already exists")

    created_at = payload.get("created_at") or _utc_now()
    row = _normalize_experiment_row(
        {
            **payload,
            "program_id": program_id,
            "experiment_id": experiment_id,
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
    _write_parquet([row], _experiment_path(storage_root, experiment_id))
    _write_json(row, _experiment_manifest_path(storage_root, experiment_id))
    register_experiment_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)
    linked_datasets = json.loads(row["linked_datasets_json"])
    attach_research_program_links(
        storage_root=storage_root,
        program_id=program_id,
        dataset_versions=linked_datasets,
        experiment_ids=[experiment_id],
        updated_by_user_id=row["created_by_user_id"],
    )
    return RegisteredExperiment(
        experiment_id=experiment_id,
        program_id=program_id,
        experiment_name=row["experiment_name"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def update_experiment(
    storage_root: Path,
    experiment_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    path = _experiment_path(storage_root, experiment_id)
    frame = _read_parquet_if_exists(path)
    if frame.empty:
        raise ValueError(f"experiment_id {experiment_id} does not exist")
    current = frame.iloc[0].to_dict()
    mutable_fields = STRING_FIELDS | JSON_LIST_FIELDS
    updates = {key: value for key, value in payload.items() if key in mutable_fields}
    if not updates:
        raise ValueError("payload must include at least one updateable experiment field")
    updated = _normalize_experiment_row(
        {
            **current,
            **updates,
            "program_id": int(current["program_id"]),
            "experiment_id": experiment_id,
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
    _write_json(updated, _experiment_manifest_path(storage_root, experiment_id))
    register_experiment_duckdb_view(
        storage_root=storage_root,
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
        replace_existing=True,
    )
    linked_datasets = json.loads(updated["linked_datasets_json"])
    attach_research_program_links(
        storage_root=storage_root,
        program_id=int(updated["program_id"]),
        dataset_versions=linked_datasets,
        experiment_ids=[experiment_id],
        run_ids=json.loads(updated["linked_run_ids_json"]),
        updated_by_user_id=updated["updated_by_user_id"],
    )
    return updated


def append_experiment_note(
    storage_root: Path,
    experiment_id: int,
    payload: dict[str, Any],
) -> ExperimentNoteResult:
    path = _experiment_path(storage_root, experiment_id)
    frame = _read_parquet_if_exists(path)
    if frame.empty:
        raise ValueError(f"experiment_id {experiment_id} does not exist")
    current = frame.iloc[0].to_dict()
    body = str(payload.get("body") or payload.get("note") or "").strip()
    if not body:
        raise ValueError("note body is required")

    notes = _note_list(current)
    note_id = int(payload.get("note_id") or _next_note_id(notes))
    note = {
        "note_id": note_id,
        "body": body,
        "author_name": str(
            payload.get("author_name")
            or payload.get("created_by_user_id")
            or current.get("updated_by_user_id")
            or current.get("owner_name")
            or "user_demo_owner"
        ),
        "created_at": str(payload.get("created_at") or _utc_now()),
    }
    notes.append(note)
    updated = update_experiment(
        storage_root=storage_root,
        experiment_id=experiment_id,
        payload={
            "notes": notes,
            "updated_by_user_id": note["author_name"],
            "updated_at": payload.get("updated_at") or note["created_at"],
        },
    )
    return ExperimentNoteResult(
        experiment_id=experiment_id,
        note_id=note_id,
        notes=json.loads(updated["notes_json"]),
        updated_at=updated["updated_at"],
    )


def attach_experiment_links(
    storage_root: Path,
    experiment_id: int,
    linked_datasets: list[dict[str, int]] | None = None,
    run_ids: list[int] | None = None,
    model_version_ids: list[int] | None = None,
    updated_by_user_id: str | None = None,
) -> dict[str, Any]:
    path = _experiment_path(storage_root, experiment_id)
    frame = _read_parquet_if_exists(path)
    if frame.empty:
        raise ValueError(f"experiment_id {experiment_id} does not exist")
    current = frame.iloc[0].to_dict()
    payload: dict[str, Any] = {
        "linked_datasets": _merge_dataset_refs(
            _linked_dataset_refs(current),
            linked_datasets or [],
        ),
        "linked_run_ids": _merge_ints(_list_value(current, "linked_run_ids"), run_ids or []),
        "linked_model_version_ids": _merge_ints(
            _list_value(current, "linked_model_version_ids"),
            model_version_ids or [],
        ),
    }
    if updated_by_user_id:
        payload["updated_by_user_id"] = updated_by_user_id
    return update_experiment(
        storage_root=storage_root,
        experiment_id=experiment_id,
        payload=payload,
    )


def register_experiment_duckdb_view(
    storage_root: Path,
    duckdb_path: Path,
    replace_existing: bool = False,
) -> None:
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    experiment_root = storage_root / "parquet" / "experiments"
    if not list(experiment_root.glob("**/*.parquet")):
        return
    if not replace_existing and _duckdb_has_table(duckdb_path, "experiments"):
        return
    pattern = str(experiment_root / "**" / "*.parquet").replace("'", "''")
    create_clause = "CREATE OR REPLACE VIEW" if replace_existing else "CREATE VIEW"
    connection = duckdb.connect(str(duckdb_path))
    try:
        try:
            connection.execute(
                f"""
                {create_clause} experiments AS
                SELECT * FROM read_parquet('{pattern}', hive_partitioning = true, union_by_name = true)
                """
            )
        except duckdb.TransactionException:
            return
    finally:
        connection.close()


def _normalize_experiment_row(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status") or "planning")
    if status not in EXPERIMENT_STATUSES:
        allowed = ", ".join(sorted(EXPERIMENT_STATUSES))
        raise ValueError(f"status must be one of: {allowed}")
    experiment_name = str(payload.get("experiment_name") or payload.get("name") or "").strip()
    if not experiment_name:
        raise ValueError("experiment_name is required")
    linked_datasets = _linked_dataset_refs(payload)
    return {
        "experiment_id": int(payload["experiment_id"]),
        "program_id": int(payload["program_id"]),
        "experiment_name": experiment_name,
        "experiment_description": str(
            payload.get("experiment_description") or payload.get("description") or ""
        ).strip(),
        "research_question": str(payload.get("research_question") or "").strip(),
        "hypothesis": str(payload.get("hypothesis") or "").strip(),
        "experiment_type": str(payload.get("experiment_type") or "").strip(),
        "status": status,
        "owner_name": str(payload.get("owner_name") or "").strip(),
        "evaluation_plan": str(payload.get("evaluation_plan") or "").strip(),
        "tags_json": json.dumps(_string_list(payload, "tags"), sort_keys=True),
        "variants_json": json.dumps(_variant_list(payload), sort_keys=True),
        "notes_json": json.dumps(_note_list(payload), sort_keys=True),
        "linked_datasets_json": json.dumps(linked_datasets, sort_keys=True),
        "linked_run_ids_json": json.dumps(
            [int(value) for value in _list_value(payload, "linked_run_ids")],
            sort_keys=True,
        ),
        "linked_model_version_ids_json": json.dumps(
            [int(value) for value in _list_value(payload, "linked_model_version_ids")],
            sort_keys=True,
        ),
        "decision_notes": str(payload.get("decision_notes") or "").strip(),
        "input_source": str(payload.get("input_source") or "ui").strip(),
        "created_at": str(payload["created_at"]),
        "updated_at": str(payload["updated_at"]),
        "created_by_user_id": str(payload.get("created_by_user_id") or "user_demo_owner"),
        "updated_by_user_id": str(payload.get("updated_by_user_id") or "user_demo_owner"),
    }


def _variant_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    variants = _list_value(payload, "variants")
    normalized: list[dict[str, Any]] = []
    for index, variant in enumerate(variants, start=1):
        if not isinstance(variant, dict):
            raise ValueError("variants must be objects")
        normalized.append(
            {
                "variant_id": int(variant.get("variant_id") or index),
                "variant_name": str(variant.get("variant_name") or variant.get("name") or "").strip(),
                "variant_type": str(
                    variant.get("variant_type") or ("control" if index == 1 else "test")
                ).strip(),
                "description": str(variant.get("description") or "").strip(),
            }
        )
    return normalized


def _note_list(payload: dict[str, Any]) -> list[dict[str, Any]]:
    notes = _list_value(payload, "notes")
    normalized: list[dict[str, Any]] = []
    for index, note in enumerate(notes, start=1):
        if isinstance(note, str):
            body = note.strip()
            author_name = str(payload.get("updated_by_user_id") or "user_demo_owner")
            created_at = str(payload.get("updated_at") or _utc_now())
            note_id = index
        elif isinstance(note, dict):
            body = str(note.get("body") or note.get("note") or "").strip()
            author_name = str(note.get("author_name") or note.get("created_by_user_id") or "")
            created_at = str(note.get("created_at") or "")
            note_id = int(note.get("note_id") or index)
        else:
            raise ValueError("notes must be strings or objects")
        if not body:
            continue
        normalized.append(
            {
                "note_id": note_id,
                "body": body,
                "author_name": author_name or "user_demo_owner",
                "created_at": created_at or _utc_now(),
            }
        )
    return normalized


def _next_note_id(notes: list[dict[str, Any]]) -> int:
    if not notes:
        return 1
    return max(int(note["note_id"]) for note in notes) + 1


def _merge_ints(existing: list[Any], additions: list[int]) -> list[int]:
    merged = {int(value) for value in existing}
    merged.update(int(value) for value in additions)
    return sorted(merged)


def _merge_dataset_refs(
    existing: list[dict[str, int]],
    additions: list[dict[str, int]],
) -> list[dict[str, int]]:
    refs = {
        (int(ref["dataset_id"]), int(ref["dataset_version_id"]))
        for ref in [*existing, *additions]
    }
    return [
        {"dataset_id": dataset_id, "dataset_version_id": dataset_version_id}
        for dataset_id, dataset_version_id in sorted(refs)
    ]


def _linked_dataset_refs(payload: dict[str, Any]) -> list[dict[str, int]]:
    raw_value = payload.get("linked_datasets")
    if raw_value is None:
        raw_value = payload.get("linked_datasets_json")
    if isinstance(raw_value, str) and raw_value:
        raw_value = json.loads(raw_value)
    if raw_value is None:
        return []
    return [
        {
            "dataset_id": int(ref["dataset_id"]),
            "dataset_version_id": int(ref["dataset_version_id"]),
        }
        for ref in list(raw_value)
    ]


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


def _next_id(duckdb_path: Path) -> int:
    if not duckdb_path.exists():
        return 1
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            value = connection.execute(
                "SELECT COALESCE(MAX(experiment_id), 0) FROM experiments"
            ).fetchone()[0]
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


def _experiment_path(storage_root: Path, experiment_id: int) -> Path:
    return (
        storage_root
        / "parquet"
        / "experiments"
        / f"experiment_id={experiment_id}"
        / "experiment.parquet"
    )


def _experiment_manifest_path(storage_root: Path, experiment_id: int) -> Path:
    return (
        storage_root
        / "object_store"
        / "experiments"
        / f"experiment_id={experiment_id}"
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
