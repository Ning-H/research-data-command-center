from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


class RunRepository:
    def __init__(self, duckdb_path: Path, storage_root: Path) -> None:
        self.duckdb_path = duckdb_path
        self.storage_root = storage_root

    def list_runs(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if not self._has_table("training_runs"):
            return []
        rows = self._query(
            """
            SELECT
                run_id,
                run_name,
                experiment_name,
                dataset_id,
                dataset_version_id,
                run_config_id,
                model_family,
                status,
                ingest_source,
                training_environment,
                raw_events_uri,
                source_priority,
                started_at,
                ended_at,
                created_by_user_id
            FROM training_runs
            ORDER BY started_at DESC
            LIMIT ? OFFSET ?
            """,
            [limit, offset],
        )
        return [self._summarize_run(row) for row in rows]

    def get_run(self, run_id: str | int) -> dict[str, Any] | None:
        if not self._has_table("training_runs"):
            return None
        rows = self._query(
            """
            SELECT
                run_id,
                run_name,
                experiment_name,
                dataset_id,
                dataset_version_id,
                run_config_id,
                model_family,
                status,
                ingest_source,
                training_environment,
                raw_events_uri,
                source_priority,
                started_at,
                ended_at,
                created_by_user_id
            FROM training_runs
            WHERE run_id = ?
            """,
            [int(run_id)],
        )
        if not rows:
            return None
        run = self._summarize_run(rows[0])
        return {
            **run,
            "run_config": self.get_run_config(run["run_config_id"]),
            "metric_series": self.get_metric_series(run_id, "train.loss"),
            "metric_summary": self.get_metric_summary(run_id),
            "compute_summary": self.get_compute_summary(run_id),
            "checkpoints": self.list_checkpoints(run_id),
            "lineage": self.get_lineage(run_id),
            "raw_ingest_summary": {
                "raw_events_uri": run["raw_events_uri"],
                "ingest_source": run["ingest_source"],
                "source_priority": run["source_priority"],
                "note": "Researcher-owned training jobs save raw events and checkpoint metadata to this platform through API/SDK calls.",
            },
        }

    def get_run_config(self, run_config_id: str | int) -> dict[str, Any]:
        if not self._has_table("run_configs"):
            return {}
        rows = self._query(
            """
            SELECT run_config_id, dataset_version_id, model_id, config_uri, config_json, created_at
            FROM run_configs
            WHERE run_config_id = ?
            """,
            [int(run_config_id)],
        )
        if not rows:
            return {}
        row = rows[0]
        return {
            **row,
            "config": json.loads(row["config_json"]) if row.get("config_json") else {},
        }

    def list_metrics(self, run_id: str | int) -> list[dict[str, Any]]:
        if not self._has_table("training_metrics"):
            return []
        return self._query(
            """
            SELECT run_id, timestamp, step, metric_name, metric_value
            FROM training_metrics
            WHERE run_id = ?
            ORDER BY step, metric_name
            """,
            [int(run_id)],
        )

    def get_metric_series(self, run_id: str | int, metric_name: str) -> list[dict[str, Any]]:
        if not self._has_table("training_metrics"):
            return []
        return self._query(
            """
            SELECT timestamp, step, metric_value
            FROM training_metrics
            WHERE run_id = ? AND metric_name = ?
            ORDER BY step
            """,
            [int(run_id), metric_name],
        )

    def list_compute_metrics(self, run_id: str | int) -> list[dict[str, Any]]:
        if not self._has_table("compute_metrics"):
            return []
        return self._query(
            """
            SELECT run_id, node_id, gpu_id, timestamp, step, metric_name, metric_value
            FROM compute_metrics
            WHERE run_id = ?
            ORDER BY step, metric_name
            """,
            [int(run_id)],
        )

    def list_checkpoints(self, run_id: str | int) -> list[dict[str, Any]]:
        if not self._has_table("checkpoints"):
            return []
        rows = self._query(
            """
            SELECT
                checkpoint_id,
                run_id,
                dataset_version_id,
                step,
                status,
                artifact_uri,
                metrics_snapshot_json,
                created_at
            FROM checkpoints
            WHERE run_id = ?
            ORDER BY step
            """,
            [int(run_id)],
        )
        return [
            {
                **row,
                "checkpoint_uri": row["artifact_uri"],
                "metrics_snapshot": json.loads(row["metrics_snapshot_json"])
                if row.get("metrics_snapshot_json")
                else {},
            }
            for row in rows
        ]

    def get_lineage(self, run_id: str | int) -> list[dict[str, Any]]:
        run = self._run_row(run_id)
        if not run:
            return []
        checkpoints = self.list_checkpoints(run_id)
        lineage = [
            {
                "lineage_step": "dataset_version_to_run_config",
                "source_type": "dataset_version",
                "source_id": run["dataset_version_id"],
                "target_type": "run_config",
                "target_id": run["run_config_id"],
            },
            {
                "lineage_step": "run_config_to_run",
                "source_type": "run_config",
                "source_id": run["run_config_id"],
                "target_type": "run",
                "target_id": run["run_id"],
            },
        ]
        lineage.extend(
            {
                "lineage_step": "run_to_checkpoint",
                "source_type": "run",
                "source_id": run["run_id"],
                "target_type": "checkpoint",
                "target_id": checkpoint["checkpoint_id"],
            }
            for checkpoint in checkpoints
        )
        return lineage

    def get_metric_summary(self, run_id: str | int) -> dict[str, Any]:
        loss_series = self.get_metric_series(run_id, "train.loss")
        token_series = self.get_metric_series(run_id, "train.tokens_seen")
        if not loss_series:
            return {}
        initial_loss = float(loss_series[0]["metric_value"])
        final_loss = float(loss_series[-1]["metric_value"])
        min_loss = min(float(row["metric_value"]) for row in loss_series)
        last_step = max(int(row["step"]) for row in loss_series)
        tokens_seen = float(token_series[-1]["metric_value"]) if token_series else 0.0
        return {
            "initial_loss": round(initial_loss, 4),
            "final_loss": round(final_loss, 4),
            "min_loss": round(min_loss, 4),
            "loss_delta_percent": round(((final_loss - initial_loss) / initial_loss) * 100, 2)
            if initial_loss
            else 0.0,
            "last_step": last_step,
            "tokens_seen": int(tokens_seen),
        }

    def get_compute_summary(self, run_id: str | int) -> dict[str, Any]:
        rows = self.list_compute_metrics(run_id)
        if not rows:
            return {}
        by_metric: dict[str, list[float]] = {}
        for row in rows:
            by_metric.setdefault(row["metric_name"], []).append(float(row["metric_value"]))
        return {
            "avg_gpu_utilization": round(_mean(by_metric.get("gpu.utilization_percent", [])), 2),
            "max_memory_used_gb": round(max(by_metric.get("gpu.memory_used_gb", [0])), 2),
            "avg_tokens_per_second": round(_mean(by_metric.get("throughput.tokens_per_second", [])), 2),
            "estimated_cost_usd": round(max(by_metric.get("cost.estimated_usd", [0])), 2),
        }

    def _summarize_run(self, row: dict[str, Any]) -> dict[str, Any]:
        metric_summary = self.get_metric_summary(row["run_id"])
        checkpoints = self.list_checkpoints(row["run_id"])
        health_summary = _health_summary(row, metric_summary, checkpoints)
        return {
            **row,
            "health_summary": health_summary,
            "checkpoint_count": len(checkpoints),
            "model_version_status": "not_promoted_yet",
        }

    def _run_row(self, run_id: str | int) -> dict[str, Any] | None:
        if not self._has_table("training_runs"):
            return None
        rows = self._query("SELECT * FROM training_runs WHERE run_id = ?", [int(run_id)])
        return rows[0] if rows else None

    def _has_table(self, table_name: str) -> bool:
        if not self.duckdb_path.exists():
            return False
        try:
            self._query(f"SELECT 1 FROM {table_name} LIMIT 1")
        except duckdb.Error:
            return False
        return True

    def _query(self, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        connection = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            result = connection.execute(query, params or [])
            columns = [column[0] for column in result.description]
            return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        finally:
            connection.close()


def _health_summary(
    run: dict[str, Any],
    metric_summary: dict[str, Any],
    checkpoints: list[dict[str, Any]],
) -> dict[str, Any]:
    status = run["status"]
    if not metric_summary:
        return {"health_score": 0, "health_label": "missing metrics", "signals": []}
    loss_delta = float(metric_summary["loss_delta_percent"])
    checkpoint_count = len(checkpoints)
    if status == "failed":
        score = 48
        label = "failed"
    else:
        score = 70
        if loss_delta < -35:
            score += 18
        elif loss_delta < -10:
            score += 8
        if checkpoint_count >= 2:
            score += 7
        score = min(score, 100)
        label = "healthy" if score >= 85 else "needs review"
    return {
        "health_score": score,
        "health_label": label,
        "signals": [
            f"status={status}",
            f"loss_delta_percent={loss_delta}",
            f"checkpoint_count={checkpoint_count}",
        ],
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
