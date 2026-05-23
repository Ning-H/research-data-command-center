from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb


class DatasetRepository:
    def __init__(self, duckdb_path: Path, storage_root: Path) -> None:
        self.duckdb_path = duckdb_path
        self.storage_root = storage_root

    def list_datasets(
        self,
        q: str | None = None,
        task_type: str | None = None,
        source_label: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self.duckdb_path.exists():
            return []
        filters: list[str] = []
        params: list[Any] = []
        if q:
            filters.append("(source_dataset_name ILIKE ? OR task_type ILIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])
        if task_type:
            filters.append("task_type = ?")
            params.append(task_type)
        if source_label:
            filters.append("source_label = ?")
            params.append(source_label)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        query = """
            WITH latest_versions AS (
                SELECT
                    dataset_id,
                    dataset_version_id,
                    source_dataset_name,
                    task_type,
                    source_label,
                    COUNT(*) AS record_count,
                    MAX(created_at) AS created_at
                FROM dataset_records
                {where_clause}
                GROUP BY 1, 2, 3, 4, 5
            ),
            quality AS (
                SELECT
                    dataset_version_id,
                    MAX(CASE WHEN metric_name = 'quality.gate_status_numeric' THEN metric_value END) AS gate_status_numeric
                FROM dataset_quality_reports
                GROUP BY 1
            )
            SELECT
                latest_versions.dataset_id,
                latest_versions.dataset_version_id,
                latest_versions.source_dataset_name,
                latest_versions.task_type,
                latest_versions.source_label,
                latest_versions.record_count,
                latest_versions.created_at,
                COALESCE(quality.gate_status_numeric, 1) AS gate_status_numeric
            FROM latest_versions
            LEFT JOIN quality USING (dataset_version_id)
            ORDER BY latest_versions.created_at DESC
            LIMIT ? OFFSET ?
        """.format(where_clause=where_clause)
        params.extend([limit, offset])
        rows = self._query(query, params)
        return [
            {
                **row,
                "name": _display_name(row["source_dataset_name"]),
                "quality_status": _quality_status(row["gate_status_numeric"]),
                "category": _category_for_task(row["task_type"]),
            }
            for row in rows
        ]

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        datasets = [dataset for dataset in self.list_datasets() if dataset["dataset_id"] == dataset_id]
        if not datasets:
            return None
        dataset = datasets[0]
        dataset_version_id = dataset["dataset_version_id"]
        return {
            **dataset,
            "description": _description_for_source(dataset["source_dataset_name"]),
            "quality_metrics": self.get_quality_metrics(dataset_id, dataset_version_id),
            "schema_profile": self.get_schema_profile(dataset_id, dataset_version_id, limit=12),
            "lineage": self.get_lineage(dataset_id, dataset_version_id),
            "sample_records": self.list_records(dataset_id, dataset_version_id, limit=10),
        }

    def list_records(
        self,
        dataset_id: str,
        dataset_version_id: str,
        limit: int = 25,
        offset: int = 0,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = ["dataset_id = ?", "dataset_version_id = ?"]
        params: list[Any] = [dataset_id, dataset_version_id]
        if q:
            filters.append(
                "(instruction ILIKE ? OR context ILIKE ? OR response_text ILIKE ? OR category ILIKE ?)"
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        params.extend([limit, offset])
        return self._query(
            f"""
            SELECT
                record_id,
                source_split,
                source_row_id,
                category,
                task_type,
                instruction,
                context,
                response_text,
                content_hash
            FROM dataset_records
            WHERE {" AND ".join(filters)}
            ORDER BY TRY_CAST(source_row_id AS INTEGER), source_row_id
            LIMIT ? OFFSET ?
            """,
            params,
        )

    def get_quality_metrics(self, dataset_id: str, dataset_version_id: str) -> list[dict[str, Any]]:
        _ = dataset_id
        return self._query(
            """
            SELECT metric_name, metric_value, source_priority, timestamp
            FROM dataset_quality_reports
            WHERE dataset_version_id = ?
            ORDER BY metric_name
            """,
            [dataset_version_id],
        )

    def get_schema_profile(
        self,
        dataset_id: str,
        dataset_version_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        _ = dataset_id
        query = """
            SELECT
                field_name,
                field_type,
                non_null_count,
                null_count,
                empty_count,
                distinct_count,
                min_length,
                max_length,
                mean_length
            FROM dataset_schema_profiles
            WHERE dataset_version_id = ?
            ORDER BY field_name
        """
        params: list[Any] = [dataset_version_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return self._query(query, params)

    def get_lineage(self, dataset_id: str, dataset_version_id: str) -> list[dict[str, Any]]:
        return self._query(
            """
            SELECT
                dataset_id,
                source_dataset_version_id,
                target_dataset_version_id,
                lineage_event_type,
                transform_name,
                transform_config_uri,
                created_at,
                created_by_user_id
            FROM dataset_lineage
            WHERE dataset_id = ? AND target_dataset_version_id = ?
            ORDER BY created_at
            """,
            [dataset_id, dataset_version_id],
        )

    def _query(self, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        connection = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            result = connection.execute(query, params or [])
            columns = [column[0] for column in result.description]
            return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        finally:
            connection.close()


def _display_name(source_dataset_name: str) -> str:
    return {
        "databricks/databricks-dolly-15k": "Databricks Dolly 15k",
        "Anthropic/hh-rlhf": "Anthropic HH-RLHF",
        "knkarthick/samsum": "SAMSum Dialogue Summarization",
        "allenai/squad": "SQuAD Question Answering",
        "openai/openai_humaneval": "OpenAI HumanEval",
    }.get(source_dataset_name, source_dataset_name)


def _category_for_task(task_type: str) -> str:
    return {
        "instruction_tuning": "Instruction tuning",
        "preference_pair": "Preference / safety",
        "summarization": "Summarization",
        "question_answering": "Question answering",
        "coding_eval": "Coding eval",
    }.get(task_type, task_type.replace("_", " ").title())


def _description_for_source(source_dataset_name: str) -> str:
    return {
        "databricks/databricks-dolly-15k": "Human-written instruction-following data used to bootstrap the dataset catalog and training-data workflow.",
        "Anthropic/hh-rlhf": "Chosen/rejected assistant responses for preference, helpfulness, and safety research workflows.",
        "knkarthick/samsum": "Dialogue-summary pairs for summarization training and evaluation workflows.",
        "allenai/squad": "Context/question/answer records for QA evaluation and optional training workflows.",
        "openai/openai_humaneval": "Python coding benchmark tasks for model evaluation and checkpoint comparison workflows.",
    }.get(source_dataset_name, "Versioned public dataset normalized into the shared research-data schema.")


def _quality_status(gate_status_numeric: float | int | None) -> str:
    return "passed" if gate_status_numeric == 0 else "warning"
