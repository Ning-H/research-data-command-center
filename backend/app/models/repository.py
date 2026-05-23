from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


class ModelRepository:
    def __init__(self, duckdb_path: Path, storage_root: Path) -> None:
        self.duckdb_path = duckdb_path
        self.storage_root = storage_root

    def list_model_versions(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if not self._has_table("model_versions"):
            return []
        rows = self._query(
            """
            SELECT *
            FROM model_versions
            ORDER BY model_version_id DESC
            LIMIT ? OFFSET ?
            """,
            [limit, offset],
        )
        return [_model_row(row) for row in rows]

    def get_model_version(self, model_version_id: int) -> dict[str, Any] | None:
        if not self._has_table("model_versions"):
            return None
        rows = self._query(
            """
            SELECT *
            FROM model_versions
            WHERE model_version_id = ?
            LIMIT 1
            """,
            [int(model_version_id)],
        )
        if not rows:
            return None
        row = _model_row(rows[0])
        row["lineage"] = self.get_lineage(model_version_id)
        return row

    def get_lineage(self, model_version_id: int) -> list[dict[str, Any]]:
        model = self._model_raw_row(model_version_id)
        if not model:
            return []
        return [
            {
                "lineage_step": "dataset_version_to_run",
                "source_type": "dataset_version",
                "source_id": model["dataset_version_id"],
                "target_type": "run",
                "target_id": model["run_id"],
            },
            {
                "lineage_step": "run_to_checkpoint",
                "source_type": "run",
                "source_id": model["run_id"],
                "target_type": "checkpoint",
                "target_id": model["checkpoint_id"],
            },
            {
                "lineage_step": "checkpoint_to_model_version",
                "source_type": "checkpoint",
                "source_id": model["checkpoint_id"],
                "target_type": "model_version",
                "target_id": model["model_version_id"],
            },
        ]

    def _model_raw_row(self, model_version_id: int) -> dict[str, Any] | None:
        if not self._has_table("model_versions"):
            return None
        rows = self._query(
            "SELECT * FROM model_versions WHERE model_version_id = ? LIMIT 1",
            [int(model_version_id)],
        )
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


def _model_row(row: dict[str, Any]) -> dict[str, Any]:
    metrics_snapshot = (
        json.loads(row["metrics_snapshot_json"]) if row.get("metrics_snapshot_json") else {}
    )
    expected_eval_suite_ids = (
        json.loads(row["expected_eval_suite_ids_json"])
        if row.get("expected_eval_suite_ids_json")
        else []
    )
    return {
        **row,
        "metrics_snapshot": metrics_snapshot,
        "expected_eval_suite_ids": expected_eval_suite_ids,
        "lineage_summary": {
            "dataset_id": row["dataset_id"],
            "dataset_version_id": row["dataset_version_id"],
            "run_id": row["run_id"],
            "checkpoint_id": row["checkpoint_id"],
            "model_version_id": row["model_version_id"],
        },
    }
