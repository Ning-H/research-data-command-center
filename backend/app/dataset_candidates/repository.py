from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb


class DatasetCandidateRepository:
    def __init__(self, duckdb_path: Path, storage_root: Path) -> None:
        self.duckdb_path = duckdb_path
        self.storage_root = storage_root

    def list_candidates(
        self,
        program_id: int | None = None,
        experiment_id: int | None = None,
        target_dataset_id: int | None = None,
        source_model_version_id: int | None = None,
        failure_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._has_table("dataset_candidates"):
            return []
        filters: list[str] = []
        params: list[Any] = []
        if program_id is not None:
            filters.append("program_id = ?")
            params.append(int(program_id))
        if experiment_id is not None:
            filters.append("experiment_id = ?")
            params.append(int(experiment_id))
        if target_dataset_id is not None:
            filters.append("target_dataset_id = ?")
            params.append(int(target_dataset_id))
        if source_model_version_id is not None:
            filters.append("source_model_version_id = ?")
            params.append(int(source_model_version_id))
        if failure_type:
            filters.append("failure_type = ?")
            params.append(failure_type)
        if status:
            filters.append("status = ?")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        return [
            _candidate_row(row)
            for row in self._query(
                f"""
                SELECT *
                FROM dataset_candidates
                {where_clause}
                ORDER BY created_at DESC, dataset_candidate_id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            )
        ]

    def get_candidate(self, dataset_candidate_id: int) -> dict[str, Any] | None:
        if not self._has_table("dataset_candidates"):
            return None
        rows = self._query(
            "SELECT * FROM dataset_candidates WHERE dataset_candidate_id = ? LIMIT 1",
            [int(dataset_candidate_id)],
        )
        if not rows:
            return None
        return _candidate_row(rows[0])

    def list_dataset_iterations(
        self,
        program_id: int | None = None,
        experiment_id: int | None = None,
        target_dataset_id: int | None = None,
        status: str | None = None,
        failure_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._has_table("dataset_candidates"):
            return []
        filters: list[str] = []
        params: list[Any] = []
        if program_id is not None:
            filters.append("program_id = ?")
            params.append(int(program_id))
        if experiment_id is not None:
            filters.append("experiment_id = ?")
            params.append(int(experiment_id))
        if target_dataset_id is not None:
            filters.append("target_dataset_id = ?")
            params.append(int(target_dataset_id))
        if status:
            filters.append("status = ?")
            params.append(status)
        if failure_type:
            filters.append("failure_type = ?")
            params.append(failure_type)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        included_count_select = "0 AS included_count"
        if self._has_column("dataset_candidates", "included_dataset_version_id"):
            included_count_select = """
                COUNT(
                    CASE
                        WHEN COALESCE(included_dataset_version_id, 0) > 0 THEN 1
                    END
                ) AS included_count
            """
        return self._query(
            f"""
            SELECT
                target_dataset_id,
                status,
                failure_type,
                source_model_version_id,
                COUNT(*) AS candidate_count,
                {included_count_select},
                MIN(created_at) AS first_created_at,
                MAX(created_at) AS last_created_at
            FROM dataset_candidates
            {where_clause}
            GROUP BY 1, 2, 3, 4
            ORDER BY target_dataset_id, status, failure_type, source_model_version_id
            """,
            params,
        )

    def _has_table(self, table_name: str) -> bool:
        if not self.duckdb_path.exists():
            return False
        try:
            self._query(f"SELECT 1 FROM {table_name} LIMIT 1")
        except duckdb.Error:
            return False
        return True

    def _has_column(self, table_name: str, column_name: str) -> bool:
        if not self.duckdb_path.exists():
            return False
        try:
            rows = self._query(f"DESCRIBE {table_name}")
        except duckdb.Error:
            return False
        return any(row.get("column_name") == column_name for row in rows)

    def _query(self, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        connection = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            result = connection.execute(query, params or [])
            columns = [column[0] for column in result.description]
            return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        finally:
            connection.close()


def _candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    hydrated = {
        "source_priority": "GENERATED_REAL",
        "reviewed_at": "",
        "reviewed_by_user_id": "",
        "included_dataset_id": 0,
        "included_dataset_version_id": 0,
        "included_at": "",
        **row,
    }
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
