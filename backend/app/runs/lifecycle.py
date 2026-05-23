from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from app.datasets.repository import _storage_dataset_id_for_display_id, _storage_version_id_for_display_id
from app.runs.ingestion import register_run_duckdb_views
from research_command_center_contract.enums import CheckpointStatus, RunStatus, SourcePriority


@dataclass(frozen=True)
class RegisteredRun:
    run_id: int
    run_config_id: int
    dataset_id: int
    dataset_version_id: int
    status: str
    raw_events_uri: str


@dataclass(frozen=True)
class AppendResult:
    run_id: int
    appended_count: int
    raw_events_uri: str


@dataclass(frozen=True)
class CompleteRunResult:
    run_id: int
    status: str
    ended_at: str


def register_run(storage_root: Path, payload: dict[str, Any]) -> RegisteredRun:
    dataset_id = int(payload["dataset_id"])
    dataset_version_id = int(payload["dataset_version_id"])
    _validate_registered_dataset(storage_root, dataset_id, dataset_version_id)

    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_run_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    run_id = int(payload.get("run_id") or _next_id(duckdb_path, "training_runs", "run_id"))
    run_config_id = int(
        payload.get("run_config_id") or _next_id(duckdb_path, "run_configs", "run_config_id")
    )
    started_at = payload.get("started_at") or _utc_now()
    created_by_user_id = payload.get("owner_user_id") or payload.get("created_by_user_id") or "user_demo_owner"
    run_config = payload.get("run_config") or {}

    raw_path = _raw_events_path(storage_root, run_id)
    _append_jsonl(
        raw_path,
        [
            {
                "event_type": "run_registered",
                "run_id": run_id,
                "timestamp": started_at,
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "run_name": payload["run_name"],
                "research_intent": payload["research_intent"],
            }
        ],
    )

    object_dir = storage_root / "object_store" / "runs" / f"run_id={run_id}"
    object_dir.mkdir(parents=True, exist_ok=True)
    config_path = object_dir / "run_config.json"
    _write_json(run_config, config_path)
    _write_json(
        {
            "run_id": run_id,
            "run_config_id": run_config_id,
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "raw_events_uri": str(raw_path),
            "artifact_root_uri": payload["artifact_root_uri"],
            "source_priority": SourcePriority.GENERATED_REAL.value,
            "note": "Run was registered by an external training script through the API/SDK.",
        },
        object_dir / "registration_manifest.json",
    )

    _write_parquet(
        [
            {
                "run_config_id": run_config_id,
                "dataset_version_id": dataset_version_id,
                "model_id": payload.get("base_model_name")
                or payload.get("parent_model_version_id")
                or "unknown",
                "config_uri": str(config_path),
                "config_json": json.dumps(run_config, sort_keys=True),
                "created_at": started_at,
                "created_by_user_id": created_by_user_id,
            }
        ],
        _run_config_path(storage_root, run_config_id),
    )
    _write_parquet(
        [
            {
                "run_id": run_id,
                "experiment_id": int(payload.get("experiment_id", 1)),
                "run_config_id": run_config_id,
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "run_name": payload["run_name"],
                "experiment_name": payload.get("experiment_name", payload["run_name"]),
                "model_family": payload.get("base_model_name")
                or payload.get("parent_model_version_id")
                or "unknown",
                "training_task": payload["training_task"],
                "research_intent": payload["research_intent"],
                "success_criteria": payload.get("success_criteria", ""),
                "planned_eval_suite_ids_json": json.dumps(
                    payload.get("planned_eval_suite_ids", []), sort_keys=True
                ),
                "artifact_root_uri": payload["artifact_root_uri"],
                "status": RunStatus.RUNNING.value,
                "ingest_source": payload.get("ingest_source", "researcher_api"),
                "training_environment": payload["training_environment"],
                "raw_events_uri": str(raw_path),
                "source_priority": SourcePriority.GENERATED_REAL.value,
                "started_at": started_at,
                "ended_at": "",
                "created_by_user_id": created_by_user_id,
            }
        ],
        _training_run_path(storage_root, run_id),
    )
    register_run_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    return RegisteredRun(
        run_id=run_id,
        run_config_id=run_config_id,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        status=RunStatus.RUNNING.value,
        raw_events_uri=str(raw_path),
    )


def append_run_events(storage_root: Path, run_id: int, payload: dict[str, Any]) -> AppendResult:
    _ensure_run_exists(storage_root, run_id)
    events = payload.get("events") or []
    if not events:
        raise ValueError("events must contain at least one event")

    raw_path = _raw_events_path(storage_root, run_id)
    _append_jsonl(
        raw_path,
        [
            {
                "event_type": "metric_event",
                "run_id": run_id,
                **event,
            }
            for event in events
        ],
    )

    metric_rows = _metric_rows_from_events(run_id, events)
    compute_rows = _compute_rows_from_events(run_id, events)
    if metric_rows:
        _append_parquet(metric_rows, _training_metrics_path(storage_root, run_id, events[0]["timestamp"]))
    if compute_rows:
        _append_parquet(compute_rows, _compute_metrics_path(storage_root, run_id, events[0]["timestamp"]))
    register_run_duckdb_views(
        storage_root=storage_root,
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
    )
    return AppendResult(run_id=run_id, appended_count=len(events), raw_events_uri=str(raw_path))


def append_run_checkpoints(storage_root: Path, run_id: int, payload: dict[str, Any]) -> AppendResult:
    _ensure_run_exists(storage_root, run_id)
    checkpoints = payload.get("checkpoints") or []
    if not checkpoints:
        raise ValueError("checkpoints must contain at least one checkpoint")

    existing = _read_parquet_if_exists(_checkpoints_path(storage_root, run_id))
    next_checkpoint_id = _next_checkpoint_id(run_id, existing)
    rows: list[dict[str, Any]] = []
    raw_events: list[dict[str, Any]] = []
    dataset_version_id = _run_dataset_version_id(storage_root, run_id)
    for offset, checkpoint in enumerate(checkpoints):
        checkpoint_id = int(checkpoint.get("checkpoint_id") or next_checkpoint_id + offset)
        created_at = checkpoint.get("created_at") or _utc_now()
        metrics_snapshot = checkpoint.get("metrics_snapshot") or {}
        artifact_uri = checkpoint.get("checkpoint_uri") or checkpoint.get("artifact_uri")
        if not artifact_uri:
            raise ValueError("checkpoint_uri or artifact_uri is required")
        row = {
            "checkpoint_id": checkpoint_id,
            "run_id": run_id,
            "dataset_version_id": dataset_version_id,
            "step": int(checkpoint["step"]),
            "status": checkpoint.get("status", CheckpointStatus.CREATED.value),
            "artifact_uri": artifact_uri,
            "metrics_snapshot_json": json.dumps(metrics_snapshot, sort_keys=True),
            "created_at": created_at,
        }
        rows.append(row)
        raw_events.append({"event_type": "checkpoint", **row})

    _append_jsonl(_raw_events_path(storage_root, run_id), raw_events)
    _append_parquet(rows, _checkpoints_path(storage_root, run_id))
    register_run_duckdb_views(
        storage_root=storage_root,
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
    )
    return AppendResult(
        run_id=run_id,
        appended_count=len(checkpoints),
        raw_events_uri=str(_raw_events_path(storage_root, run_id)),
    )


def complete_run(storage_root: Path, run_id: int, payload: dict[str, Any]) -> CompleteRunResult:
    _ensure_run_exists(storage_root, run_id)
    status = payload.get("status", RunStatus.COMPLETED.value)
    if status not in {RunStatus.COMPLETED.value, RunStatus.FAILED.value, RunStatus.KILLED.value}:
        raise ValueError("status must be completed, failed, or killed")
    ended_at = payload.get("ended_at") or _utc_now()

    path = _training_run_path(storage_root, run_id)
    frame = _read_parquet_if_exists(path)
    if frame.empty:
        raise ValueError(f"run_id {run_id} does not exist")
    frame.loc[:, "status"] = status
    frame.loc[:, "ended_at"] = ended_at
    frame.to_parquet(path, index=False)
    _append_jsonl(
        _raw_events_path(storage_root, run_id),
        [{"event_type": "run_completed", "run_id": run_id, "status": status, "timestamp": ended_at}],
    )
    register_run_duckdb_views(
        storage_root=storage_root,
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
    )
    return CompleteRunResult(run_id=run_id, status=status, ended_at=ended_at)


def _validate_registered_dataset(storage_root: Path, dataset_id: int, dataset_version_id: int) -> None:
    try:
        storage_dataset_id = _storage_dataset_id_for_display_id(dataset_id)
        storage_dataset_version_id = _storage_version_id_for_display_id(dataset_id, dataset_version_id)
    except KeyError as exc:
        raise ValueError(
            f"dataset_id={dataset_id}, dataset_version_id={dataset_version_id} is not registered"
        ) from exc
    records_dir = (
        storage_root
        / "parquet"
        / "dataset_records"
        / f"dataset_id={storage_dataset_id}"
        / f"dataset_version_id={storage_dataset_version_id}"
    )
    if not records_dir.exists() or not list(records_dir.glob("**/*.parquet")):
        raise ValueError(
            f"dataset_id={dataset_id}, dataset_version_id={dataset_version_id} has no Parquet records"
        )


def _ensure_run_exists(storage_root: Path, run_id: int) -> None:
    if not _training_run_path(storage_root, run_id).exists():
        raise ValueError(f"run_id {run_id} is not registered")


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


def _next_checkpoint_id(run_id: int, existing: pd.DataFrame) -> int:
    if existing.empty:
        return run_id * 1000 + 1
    return int(existing["checkpoint_id"].max()) + 1


def _run_dataset_version_id(storage_root: Path, run_id: int) -> int:
    frame = _read_parquet_if_exists(_training_run_path(storage_root, run_id))
    if frame.empty:
        raise ValueError(f"run_id {run_id} is not registered")
    return int(frame.iloc[0]["dataset_version_id"])


def _metric_rows_from_events(run_id: int, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        for metric_name, metric_value in (event.get("metrics") or {}).items():
            rows.append(
                {
                    "run_id": run_id,
                    "timestamp": event["timestamp"],
                    "step": int(event["step"]),
                    "metric_name": metric_name,
                    "metric_value": float(metric_value),
                }
            )
    return rows


def _compute_rows_from_events(run_id: int, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        compute_metrics = event.get("compute_metrics") or {}
        for metric_name, metric_value in compute_metrics.items():
            rows.append(
                {
                    "run_id": run_id,
                    "node_id": event.get("node_id", "local_node"),
                    "gpu_id": event.get("gpu_id", "none"),
                    "timestamp": event["timestamp"],
                    "step": int(event["step"]),
                    "metric_name": metric_name,
                    "metric_value": float(metric_value),
                }
            )
    return rows


def _append_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_parquet_if_exists(path)
    incoming = pd.DataFrame(rows)
    if existing.empty:
        incoming.to_parquet(path, index=False)
        return
    pd.concat([existing, incoming], ignore_index=True).to_parquet(path, index=False)


def _read_parquet_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line_prefix = "\n" if path.exists() and path.stat().st_size > 0 else ""
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line_prefix + "\n".join(json.dumps(record, ensure_ascii=True) for record in records))


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _date_from_timestamp(timestamp: str) -> str:
    return timestamp[:10]


def _raw_events_path(storage_root: Path, run_id: int) -> Path:
    return storage_root / "raw" / "runs" / f"run_id={run_id}" / "events.jsonl"


def _run_config_path(storage_root: Path, run_config_id: int) -> Path:
    return storage_root / "parquet" / "run_configs" / f"run_config_id={run_config_id}" / "config.parquet"


def _training_run_path(storage_root: Path, run_id: int) -> Path:
    return storage_root / "parquet" / "training_runs" / f"run_id={run_id}" / "run.parquet"


def _training_metrics_path(storage_root: Path, run_id: int, timestamp: str) -> Path:
    return (
        storage_root
        / "parquet"
        / "training_metrics"
        / f"run_id={run_id}"
        / f"date={_date_from_timestamp(timestamp)}"
        / "metrics.parquet"
    )


def _compute_metrics_path(storage_root: Path, run_id: int, timestamp: str) -> Path:
    return (
        storage_root
        / "parquet"
        / "compute_metrics"
        / f"run_id={run_id}"
        / f"date={_date_from_timestamp(timestamp)}"
        / "metrics.parquet"
    )


def _checkpoints_path(storage_root: Path, run_id: int) -> Path:
    return storage_root / "parquet" / "checkpoints" / f"run_id={run_id}" / "checkpoints.parquet"
