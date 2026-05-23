from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.runs.ingestion import register_run_duckdb_views
from research_command_center_contract.enums import (
    CheckpointStatus,
    ModelVersionStatus,
    SourcePriority,
)


@dataclass(frozen=True)
class RegisteredModelVersion:
    model_id: int
    model_version_id: int
    checkpoint_id: int
    run_id: int
    dataset_id: int
    dataset_version_id: int
    status: str
    artifact_uri: str


def register_model_from_checkpoint(
    storage_root: Path,
    payload: dict[str, Any],
) -> RegisteredModelVersion:
    checkpoint_id = int(payload["checkpoint_id"])
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_model_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    checkpoint = _checkpoint_context(duckdb_path=duckdb_path, checkpoint_id=checkpoint_id)
    if checkpoint is None:
        raise ValueError(f"checkpoint_id {checkpoint_id} does not exist")

    created_at = payload.get("created_at") or _utc_now()
    model_name = payload.get("model_name") or f"checkpoint-{checkpoint_id}-model"
    existing_model_id = _model_id_for_name(duckdb_path=duckdb_path, model_name=model_name)
    model_id = int(payload.get("model_id") or existing_model_id or _next_id(duckdb_path, "model_versions", "model_id"))
    model_version_id = int(
        payload.get("model_version_id")
        or _next_id(duckdb_path, "model_versions", "model_version_id")
    )
    model_version_name = payload.get("model_version_name") or f"{model_name}-checkpoint-{checkpoint_id}"
    created_by_user_id = (
        payload.get("owner_user_id")
        or payload.get("created_by_user_id")
        or checkpoint.get("created_by_user_id")
        or "user_demo_owner"
    )

    artifact_uri = checkpoint["artifact_uri"]
    manifest_path = _model_manifest_path(storage_root, model_id, model_version_id)
    manifest = {
        "model_id": model_id,
        "model_version_id": model_version_id,
        "model_name": model_name,
        "model_version_name": model_version_name,
        "checkpoint_id": checkpoint_id,
        "run_id": checkpoint["run_id"],
        "dataset_id": checkpoint["dataset_id"],
        "dataset_version_id": checkpoint["dataset_version_id"],
        "artifact_uri": artifact_uri,
        "source_priority": SourcePriority.GENERATED_REAL.value,
        "created_at": created_at,
    }
    _write_json(manifest, manifest_path)

    row = {
        "model_id": model_id,
        "model_version_id": model_version_id,
        "model_name": model_name,
        "model_version_name": model_version_name,
        "checkpoint_id": checkpoint_id,
        "run_id": int(checkpoint["run_id"]),
        "dataset_id": int(checkpoint["dataset_id"]),
        "dataset_version_id": int(checkpoint["dataset_version_id"]),
        "run_config_id": int(checkpoint["run_config_id"]),
        "source_run_name": checkpoint["run_name"],
        "source_experiment_name": checkpoint["experiment_name"],
        "base_model_name": checkpoint["model_family"],
        "source_checkpoint_step": int(checkpoint["step"]),
        "status": payload.get("status", ModelVersionStatus.CANDIDATE.value),
        "artifact_uri": artifact_uri,
        "registry_manifest_uri": str(manifest_path),
        "intended_use": payload.get("intended_use", ""),
        "promotion_reason": payload.get("promotion_reason", ""),
        "promotion_notes": payload.get("promotion_notes", ""),
        "expected_eval_suite_ids_json": json.dumps(
            payload.get("expected_eval_suite_ids", []),
            sort_keys=True,
        ),
        "metrics_snapshot_json": checkpoint.get("metrics_snapshot_json") or "{}",
        "source_priority": SourcePriority.GENERATED_REAL.value,
        "created_at": created_at,
        "created_by_user_id": created_by_user_id,
    }
    _write_parquet([row], _model_version_path(storage_root, model_version_id))
    _mark_checkpoint_promoted(storage_root=storage_root, checkpoint=checkpoint)
    register_model_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)

    return RegisteredModelVersion(
        model_id=model_id,
        model_version_id=model_version_id,
        checkpoint_id=checkpoint_id,
        run_id=int(checkpoint["run_id"]),
        dataset_id=int(checkpoint["dataset_id"]),
        dataset_version_id=int(checkpoint["dataset_version_id"]),
        status=row["status"],
        artifact_uri=artifact_uri,
    )


def register_model_duckdb_views(storage_root: Path, duckdb_path: Path) -> None:
    register_run_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(duckdb_path))
    try:
        pattern = storage_root / "parquet" / "model_versions" / "**" / "*.parquet"
        if not list((storage_root / "parquet" / "model_versions").glob("**/*.parquet")):
            return
        escaped_pattern = str(pattern).replace("'", "''")
        connection.execute(
            f"""
            CREATE OR REPLACE VIEW model_versions AS
            SELECT * FROM read_parquet('{escaped_pattern}', hive_partitioning = true, union_by_name = true)
            """
        )
    finally:
        connection.close()


def _checkpoint_context(duckdb_path: Path, checkpoint_id: int) -> dict[str, Any] | None:
    if not duckdb_path.exists():
        return None
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            row = connection.execute(
                """
                SELECT
                    cp.checkpoint_id,
                    cp.run_id,
                    tr.dataset_id,
                    cp.dataset_version_id,
                    tr.run_config_id,
                    tr.run_name,
                    tr.experiment_name,
                    tr.model_family,
                    tr.status AS run_status,
                    tr.created_by_user_id,
                    cp.step,
                    cp.status AS checkpoint_status,
                    cp.artifact_uri,
                    cp.metrics_snapshot_json,
                    cp.created_at AS checkpoint_created_at
                FROM checkpoints cp
                JOIN training_runs tr ON cp.run_id = tr.run_id
                WHERE cp.checkpoint_id = ?
                LIMIT 1
                """,
                [checkpoint_id],
            ).fetchone()
        except duckdb.Error:
            return None
        if row is None:
            return None
        columns = [column[0] for column in connection.description]
        return dict(zip(columns, row, strict=True))
    finally:
        connection.close()


def _model_id_for_name(duckdb_path: Path, model_name: str) -> int | None:
    if not duckdb_path.exists():
        return None
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            row = connection.execute(
                "SELECT MIN(model_id) FROM model_versions WHERE model_name = ?",
                [model_name],
            ).fetchone()
        except duckdb.Error:
            return None
        if not row or row[0] is None:
            return None
        return int(row[0])
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


def _mark_checkpoint_promoted(storage_root: Path, checkpoint: dict[str, Any]) -> None:
    path = storage_root / "parquet" / "checkpoints" / f"run_id={int(checkpoint['run_id'])}" / "checkpoints.parquet"
    frame = _read_parquet_if_exists(path)
    if frame.empty:
        return
    frame.loc[frame["checkpoint_id"] == int(checkpoint["checkpoint_id"]), "status"] = CheckpointStatus.PROMOTED.value
    frame.to_parquet(path, index=False)


def _model_version_path(storage_root: Path, model_version_id: int) -> Path:
    return (
        storage_root
        / "parquet"
        / "model_versions"
        / f"model_version_id={model_version_id}"
        / "model_version.parquet"
    )


def _model_manifest_path(storage_root: Path, model_id: int, model_version_id: int) -> Path:
    return (
        storage_root
        / "object_store"
        / "models"
        / f"model_id={model_id}"
        / f"model_version_id={model_version_id}"
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
