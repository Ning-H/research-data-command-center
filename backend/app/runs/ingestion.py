from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from research_command_center_contract.enums import SourcePriority

DEFAULT_OWNER_USER_ID = "user_demo_owner"


@dataclass(frozen=True)
class RunIngestionResult:
    run_id: int
    run_config_id: int
    dataset_version_id: int
    checkpoint_count: int
    raw_events_uri: str
    duckdb_path: str


def seed_demo_runs(storage_root: Path) -> list[RunIngestionResult]:
    return [ingest_run_payload(storage_root, payload) for payload in build_demo_run_payloads()]


def build_demo_run_payloads() -> list[dict[str, Any]]:
    return [
        _demo_payload(
            run_id=1,
            run_config_id=1,
            dataset_id=1,
            dataset_version_id=1,
            run_name="dolly-instruction-ft-v1",
            experiment_name="instruction-tuning-baseline",
            model_family="tiny-transformer-demo",
            status="completed",
            started_at="2026-05-23T01:40:00Z",
            step_count=1000,
            initial_loss=2.65,
            final_loss=1.18,
            tokens_per_step=18500,
            checkpoint_steps=(250, 500, 1000),
        ),
        _demo_payload(
            run_id=2,
            run_config_id=2,
            dataset_id=2,
            dataset_version_id=1,
            run_name="hh-rlhf-preference-ft-v1",
            experiment_name="preference-safety-ablation",
            model_family="tiny-reward-model-demo",
            status="completed",
            started_at="2026-05-23T01:55:00Z",
            step_count=800,
            initial_loss=1.92,
            final_loss=0.94,
            tokens_per_step=12800,
            checkpoint_steps=(200, 400, 800),
        ),
        _demo_payload(
            run_id=3,
            run_config_id=3,
            dataset_id=3,
            dataset_version_id=1,
            run_name="samsum-summarization-ft-v1",
            experiment_name="summarization-smoke-test",
            model_family="tiny-seq2seq-demo",
            status="failed",
            started_at="2026-05-23T02:10:00Z",
            step_count=650,
            initial_loss=2.2,
            final_loss=3.4,
            tokens_per_step=10400,
            checkpoint_steps=(200, 400),
            divergence_step=500,
        ),
    ]


def ingest_run_payload(storage_root: Path, payload: dict[str, Any]) -> RunIngestionResult:
    run_id = int(payload["run_id"])
    run_config_id = int(payload["run_config_id"])
    dataset_version_id = int(payload["dataset_version_id"])
    raw_events = _raw_events_from_payload(payload)
    raw_path = storage_root / "raw" / "runs" / f"run_id={run_id}" / "events.jsonl"
    _write_jsonl(raw_events, raw_path)

    object_dir = storage_root / "object_store" / "runs" / f"run_id={run_id}"
    object_dir.mkdir(parents=True, exist_ok=True)
    _write_json(payload["run_config"], object_dir / "run_config.json")
    _write_json(
        {
            "run_id": run_id,
            "raw_events_uri": str(raw_path),
            "ingest_source": payload["ingest_source"],
            "created_at": payload["ingested_at"],
            "source_priority": SourcePriority.GENERATED_REAL.value,
            "note": "Demo raw run events represent API/SDK submissions from a researcher-owned training job.",
        },
        object_dir / "ingestion_manifest.json",
    )

    _write_parquet([_run_config_row(payload, object_dir / "run_config.json")], _run_config_path(storage_root, run_config_id))
    _write_parquet([_training_run_row(payload, raw_path)], _training_run_path(storage_root, run_id))
    _write_parquet(_training_metric_rows(payload), _training_metrics_path(storage_root, run_id))
    _write_parquet(_compute_metric_rows(payload), _compute_metrics_path(storage_root, run_id))
    _write_parquet(_checkpoint_rows(payload), _checkpoints_path(storage_root, run_id))

    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_run_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)

    return RunIngestionResult(
        run_id=run_id,
        run_config_id=run_config_id,
        dataset_version_id=dataset_version_id,
        checkpoint_count=len(payload["checkpoints"]),
        raw_events_uri=str(raw_path),
        duckdb_path=str(duckdb_path),
    )


def register_run_duckdb_views(storage_root: Path, duckdb_path: Path) -> None:
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(duckdb_path))
    try:
        view_patterns = {
            "run_configs": storage_root / "parquet" / "run_configs" / "**" / "*.parquet",
            "training_runs": storage_root / "parquet" / "training_runs" / "**" / "*.parquet",
            "training_metrics": storage_root / "parquet" / "training_metrics" / "**" / "*.parquet",
            "compute_metrics": storage_root / "parquet" / "compute_metrics" / "**" / "*.parquet",
            "checkpoints": storage_root / "parquet" / "checkpoints" / "**" / "*.parquet",
        }
        for view_name, pattern in view_patterns.items():
            if not list(pattern.parent.parent.glob("**/*.parquet")):
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


def _demo_payload(
    run_id: int,
    run_config_id: int,
    dataset_id: int,
    dataset_version_id: int,
    run_name: str,
    experiment_name: str,
    model_family: str,
    status: str,
    started_at: str,
    step_count: int,
    initial_loss: float,
    final_loss: float,
    tokens_per_step: int,
    checkpoint_steps: tuple[int, ...],
    divergence_step: int | None = None,
) -> dict[str, Any]:
    events = _metric_events(
        started_at=started_at,
        step_count=step_count,
        initial_loss=initial_loss,
        final_loss=final_loss,
        tokens_per_step=tokens_per_step,
        divergence_step=divergence_step,
    )
    ended_at = events[-1]["timestamp"]
    checkpoints = [
        {
            "checkpoint_id": run_id * 100 + index,
            "run_id": run_id,
            "dataset_version_id": dataset_version_id,
            "step": step,
            "status": "created",
            "checkpoint_uri": f"s3://research-runs/{run_name}/checkpoints/step-{step}",
            "created_at": next(event["timestamp"] for event in events if event["step"] == step),
            "metrics_snapshot": _metrics_at_step(events, step),
        }
        for index, step in enumerate(checkpoint_steps, start=1)
    ]
    return {
        "run_id": run_id,
        "run_config_id": run_config_id,
        "experiment_id": 1,
        "run_name": run_name,
        "experiment_name": experiment_name,
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "created_by_user_id": DEFAULT_OWNER_USER_ID,
        "ingested_at": ended_at,
        "ingest_source": "researcher_sdk_demo",
        "training_environment": "researcher_managed_gpu_job",
        "model_family": model_family,
        "raw_metric_events": events,
        "checkpoints": checkpoints,
        "run_config": {
            "model_family": model_family,
            "optimizer": "adamw",
            "learning_rate": 0.0002,
            "batch_size": 16,
            "max_steps": step_count,
            "dataset_version_id": dataset_version_id,
            "logging_mode": "api_sdk_raw_events",
        },
    }


def _metric_events(
    started_at: str,
    step_count: int,
    initial_loss: float,
    final_loss: float,
    tokens_per_step: int,
    divergence_step: int | None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index, step in enumerate(range(0, step_count + 1, 50)):
        progress = step / step_count if step_count else 1
        if divergence_step is not None and step >= divergence_step:
            loss = final_loss - 0.35 + (step - divergence_step) * 0.004
            grad_norm = 4.4 + (step - divergence_step) * 0.01
        else:
            loss = final_loss + (initial_loss - final_loss) * math.exp(-3.2 * progress)
            grad_norm = max(0.4, 2.4 * math.exp(-2.5 * progress))
        lr = 0.0002 * max(0.05, 1 - progress * 0.92)
        tokens_seen = step * tokens_per_step
        tokens_per_second = max(600.0, tokens_per_step / 2.8 * (1 - 0.08 * math.sin(index)))
        events.append(
            {
                "timestamp": _add_minutes(started_at, index * 3),
                "step": step,
                "metrics": {
                    "train.loss": round(loss, 4),
                    "train.learning_rate": round(lr, 8),
                    "train.grad_norm": round(grad_norm, 4),
                    "train.tokens_seen": float(tokens_seen),
                    "train.tokens_per_second": round(tokens_per_second, 2),
                },
            }
        )
    return events


def _training_metric_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in payload["raw_metric_events"]:
        for metric_name, metric_value in event["metrics"].items():
            rows.append(
                {
                    "run_id": payload["run_id"],
                    "timestamp": event["timestamp"],
                    "step": event["step"],
                    "metric_name": metric_name,
                    "metric_value": float(metric_value),
                }
            )
    return rows


def _compute_metric_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    failed = payload["status"] == "failed"
    for event in payload["raw_metric_events"]:
        step = int(event["step"])
        tps = float(event["metrics"]["train.tokens_per_second"])
        if failed and step > max(checkpoint["step"] for checkpoint in payload["checkpoints"]):
            gpu_util = max(12.0, 52.0 - (step / 20))
            memory_gb = 18.5
        else:
            gpu_util = min(96.0, 58.0 + tps / 230)
            memory_gb = min(24.0, 13.5 + step / 280)
        compute_values = {
            "gpu.utilization_percent": round(gpu_util, 2),
            "gpu.memory_used_gb": round(memory_gb, 2),
            "throughput.tokens_per_second": round(tps, 2),
            "cost.estimated_usd": round(step * 0.00042, 4),
        }
        for metric_name, metric_value in compute_values.items():
            rows.append(
                {
                    "run_id": payload["run_id"],
                    "node_id": "node_1",
                    "gpu_id": "gpu_0",
                    "timestamp": event["timestamp"],
                    "step": step,
                    "metric_name": metric_name,
                    "metric_value": float(metric_value),
                }
            )
    return rows


def _checkpoint_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "checkpoint_id": checkpoint["checkpoint_id"],
            "run_id": payload["run_id"],
            "dataset_version_id": payload["dataset_version_id"],
            "step": checkpoint["step"],
            "status": checkpoint["status"],
            "artifact_uri": checkpoint["checkpoint_uri"],
            "metrics_snapshot_json": json.dumps(checkpoint["metrics_snapshot"], sort_keys=True),
            "created_at": checkpoint["created_at"],
        }
        for checkpoint in payload["checkpoints"]
    ]


def _run_config_row(payload: dict[str, Any], config_path: Path) -> dict[str, Any]:
    return {
        "run_config_id": payload["run_config_id"],
        "dataset_version_id": payload["dataset_version_id"],
        "model_id": payload["model_family"],
        "config_uri": str(config_path),
        "config_json": json.dumps(payload["run_config"], sort_keys=True),
        "created_at": payload["started_at"],
    }


def _training_run_row(payload: dict[str, Any], raw_path: Path) -> dict[str, Any]:
    return {
        "run_id": payload["run_id"],
        "experiment_id": payload["experiment_id"],
        "run_config_id": payload["run_config_id"],
        "dataset_id": payload["dataset_id"],
        "dataset_version_id": payload["dataset_version_id"],
        "run_name": payload["run_name"],
        "experiment_name": payload["experiment_name"],
        "model_family": payload["model_family"],
        "status": payload["status"],
        "ingest_source": payload["ingest_source"],
        "training_environment": payload["training_environment"],
        "raw_events_uri": str(raw_path),
        "source_priority": SourcePriority.GENERATED_REAL.value,
        "started_at": payload["started_at"],
        "ended_at": payload["ended_at"],
        "created_by_user_id": payload["created_by_user_id"],
    }


def _raw_events_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    events = [
        {
            "event_type": "metric_batch",
            "run_id": payload["run_id"],
            "timestamp": event["timestamp"],
            "step": event["step"],
            "metrics": event["metrics"],
        }
        for event in payload["raw_metric_events"]
    ]
    events.extend(
        {
            "event_type": "checkpoint",
            "run_id": payload["run_id"],
            **checkpoint,
        }
        for checkpoint in payload["checkpoints"]
    )
    return events


def _metrics_at_step(events: list[dict[str, Any]], step: int) -> dict[str, float]:
    return next(event["metrics"] for event in events if int(event["step"]) == step)


def _add_minutes(timestamp: str, minutes: int) -> str:
    from datetime import datetime, timedelta, timezone

    base = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return (base + timedelta(minutes=minutes)).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_config_path(storage_root: Path, run_config_id: int) -> Path:
    return storage_root / "parquet" / "run_configs" / f"run_config_id={run_config_id}" / "config.parquet"


def _training_run_path(storage_root: Path, run_id: int) -> Path:
    return storage_root / "parquet" / "training_runs" / f"run_id={run_id}" / "run.parquet"


def _training_metrics_path(storage_root: Path, run_id: int) -> Path:
    return storage_root / "parquet" / "training_metrics" / f"run_id={run_id}" / "date=2026-05-23" / "metrics.parquet"


def _compute_metrics_path(storage_root: Path, run_id: int) -> Path:
    return storage_root / "parquet" / "compute_metrics" / f"run_id={run_id}" / "date=2026-05-23" / "metrics.parquet"


def _checkpoints_path(storage_root: Path, run_id: int) -> Path:
    return storage_root / "parquet" / "checkpoints" / f"run_id={run_id}" / "checkpoints.parquet"


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=True) for record in records), encoding="utf-8")
