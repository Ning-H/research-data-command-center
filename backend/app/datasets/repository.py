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
                    MIN(created_at) AS registration_date,
                    MAX(created_at) AS last_updated_date
                FROM dataset_records
                {where_clause}
                GROUP BY 1, 2, 3, 4, 5
            ),
            quality AS (
                SELECT
                    dataset_version_id,
                    MAX(CASE WHEN metric_name = 'quality.gate_status_numeric' THEN metric_value END) AS gate_status_numeric,
                    MAX(CASE WHEN metric_name = 'records.total' THEN metric_value END) AS records_total,
                    MAX(CASE WHEN metric_name = 'records.empty_required_field_count' THEN metric_value END) AS required_empty_count,
                    MAX(CASE WHEN metric_name = 'records.duplicate_exact_count' THEN metric_value END) AS duplicate_count,
                    MAX(CASE WHEN metric_name = 'pii.fake_test_match_count' THEN metric_value END) AS pii_match_count
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
                latest_versions.registration_date,
                latest_versions.last_updated_date,
                COALESCE(quality.gate_status_numeric, 1) AS gate_status_numeric,
                COALESCE(quality.records_total, latest_versions.record_count) AS records_total,
                COALESCE(quality.required_empty_count, 0) AS required_empty_count,
                COALESCE(quality.duplicate_count, 0) AS duplicate_count,
                COALESCE(quality.pii_match_count, 0) AS pii_match_count
            FROM latest_versions
            LEFT JOIN quality USING (dataset_version_id)
            ORDER BY latest_versions.last_updated_date DESC
            LIMIT ? OFFSET ?
        """.format(where_clause=where_clause)
        params.extend([limit, offset])
        rows = self._query(query, params)
        return [
            _dataset_summary_from_row(row)
            for row in rows
        ]

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        datasets = [dataset for dataset in self.list_datasets() if str(dataset["dataset_id"]) == str(dataset_id)]
        if not datasets:
            return None
        dataset = datasets[0]
        storage_dataset_id = _storage_dataset_id_for_display_id(dataset["dataset_id"])
        storage_dataset_version_id = _storage_version_id_for_display_id(dataset["dataset_id"], dataset["dataset_version_id"])
        quality_metrics = self._get_quality_metrics_by_storage_version(storage_dataset_version_id)
        full_schema_profile = self._get_schema_profile_by_storage_version(storage_dataset_version_id)
        schema_profile = full_schema_profile[:12]
        return {
            **dataset,
            "quality_metrics": quality_metrics,
            "schema_profile": schema_profile,
            "quality_summary": _quality_summary(
                quality_metrics=quality_metrics,
                schema_profile=full_schema_profile,
                task_type=dataset["task_type"],
                quality_status=dataset["quality_status"],
            ),
            "lineage": self._get_lineage_by_storage_ids(storage_dataset_id, storage_dataset_version_id),
            "sample_records": self.list_records(str(dataset["dataset_id"]), str(dataset["dataset_version_id"]), limit=10),
        }

    def list_records(
        self,
        dataset_id: str,
        dataset_version_id: str,
        limit: int = 25,
        offset: int = 0,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        storage_dataset_id = _storage_dataset_id_for_display_id(dataset_id)
        storage_dataset_version_id = _storage_version_id_for_display_id(dataset_id, dataset_version_id)
        filters = ["dataset_id = ?", "dataset_version_id = ?"]
        params: list[Any] = [storage_dataset_id, storage_dataset_version_id]
        if q:
            filters.append(
                "(instruction ILIKE ? OR context ILIKE ? OR response_text ILIKE ? OR category ILIKE ?)"
            )
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%"])
        params.extend([limit, offset])
        return self._query(
            f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY TRY_CAST(source_row_id AS INTEGER), source_row_id) + ? AS record_id,
                source_split,
                source_row_id,
                category,
                task_type,
                input_text,
                instruction,
                context,
                question,
                chosen_text,
                rejected_text,
                target_text,
                response_text,
                content_hash
            FROM dataset_records
            WHERE {" AND ".join(filters)}
            ORDER BY TRY_CAST(source_row_id AS INTEGER), source_row_id
            LIMIT ? OFFSET ?
            """,
            [offset, *params],
        )

    def get_quality_metrics(self, dataset_id: str, dataset_version_id: str) -> list[dict[str, Any]]:
        _ = dataset_id
        storage_dataset_version_id = _storage_version_id_for_display_id(dataset_id, dataset_version_id)
        return self._get_quality_metrics_by_storage_version(storage_dataset_version_id)

    def _get_quality_metrics_by_storage_version(self, storage_dataset_version_id: str) -> list[dict[str, Any]]:
        return self._query(
            """
            SELECT metric_name, metric_value, source_priority, timestamp
            FROM dataset_quality_reports
            WHERE dataset_version_id = ?
            ORDER BY metric_name
            """,
            [storage_dataset_version_id],
        )

    def get_schema_profile(
        self,
        dataset_id: str,
        dataset_version_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        _ = dataset_id
        storage_dataset_version_id = _storage_version_id_for_display_id(dataset_id, dataset_version_id)
        return self._get_schema_profile_by_storage_version(storage_dataset_version_id, limit=limit)

    def _get_schema_profile_by_storage_version(
        self,
        storage_dataset_version_id: str,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
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
        params: list[Any] = [storage_dataset_version_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return self._query(query, params)

    def get_lineage(self, dataset_id: str, dataset_version_id: str) -> list[dict[str, Any]]:
        storage_dataset_id = _storage_dataset_id_for_display_id(dataset_id)
        storage_dataset_version_id = _storage_version_id_for_display_id(dataset_id, dataset_version_id)
        return self._get_lineage_by_storage_ids(storage_dataset_id, storage_dataset_version_id)

    def _get_lineage_by_storage_ids(
        self,
        storage_dataset_id: str,
        storage_dataset_version_id: str,
    ) -> list[dict[str, Any]]:
        rows = self._query(
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
            [storage_dataset_id, storage_dataset_version_id],
        )
        return [
            {
                "dataset_id": _dataset_display_id_for_storage_id(row["dataset_id"]),
                "source_dataset_version_id": "",
                "target_dataset_version_id": 1,
                "source_label": "public source",
                "lineage_event_type": row["lineage_event_type"],
                "transform_name": row["transform_name"],
                "transform_config_uri": row["transform_config_uri"],
                "created_at": row["created_at"],
                "created_by_user_id": row["created_by_user_id"],
            }
            for row in rows
        ]

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


def _dataset_display_id(source_dataset_name: str) -> int:
    return {
        "databricks/databricks-dolly-15k": 1,
        "Anthropic/hh-rlhf": 2,
        "knkarthick/samsum": 3,
        "allenai/squad": 4,
        "openai/openai_humaneval": 5,
    }.get(source_dataset_name, 0)


def _dataset_display_id_for_storage_id(dataset_id: str) -> int:
    return {
        "ds_databricks_dolly_15k": 1,
        "ds_anthropic_hh_rlhf": 2,
        "ds_samsum": 3,
        "ds_squad": 4,
        "ds_openai_humaneval": 5,
    }.get(dataset_id, 0)


def _storage_dataset_id_for_display_id(dataset_id: str | int) -> str:
    return {
        "1": "ds_databricks_dolly_15k",
        "2": "ds_anthropic_hh_rlhf",
        "3": "ds_samsum",
        "4": "ds_squad",
        "5": "ds_openai_humaneval",
    }[str(dataset_id)]


def _storage_version_id_for_display_id(dataset_id: str | int, dataset_version_id: str | int) -> str:
    if str(dataset_version_id) != "1":
        raise KeyError(f"Unknown dataset_version_id {dataset_version_id} for dataset_id {dataset_id}")
    return {
        "1": "dsv_databricks_dolly_15k_raw_v1_b66c4cf8e4",
        "2": "dsv_anthropic_hh_rlhf_raw_v1_7b57e8e5e3",
        "3": "dsv_samsum_raw_v1_89e5308a7f",
        "4": "dsv_squad_raw_v1_825c43a962",
        "5": "dsv_openai_humaneval_raw_v1_527d4f2ddd",
    }[str(dataset_id)]


def _source_url(source_dataset_name: str) -> str:
    return f"https://huggingface.co/datasets/{source_dataset_name}"


def _category_for_task(task_type: str) -> str:
    return {
        "instruction_tuning": "Instruction tuning",
        "preference_pair": "Preference / safety",
        "summarization": "Summarization",
        "question_answering": "Question answering",
        "coding_eval": "Coding eval",
    }.get(task_type, task_type.replace("_", " ").title())


def _data_purpose(task_type: str) -> str:
    return {
        "instruction_tuning": "Training data for instruction tuning",
        "preference_pair": "Preference and safety alignment data",
        "summarization": "Summarization training or evaluation data",
        "question_answering": "Question-answering evaluation data",
        "coding_eval": "Coding evaluation benchmark data",
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
    return "ready" if gate_status_numeric == 0 else "review"


def _dataset_summary_from_row(row: dict[str, Any]) -> dict[str, Any]:
    quality_score = _quality_score_from_values(
        records_total=float(row["records_total"] or row["record_count"] or 0),
        required_empty_count=float(row["required_empty_count"] or 0),
        duplicate_count=float(row["duplicate_count"] or 0),
        pii_match_count=float(row["pii_match_count"] or 0),
        profile_available=True,
    )
    return {
        "dataset_id": _dataset_display_id(row["source_dataset_name"]),
        "dataset_version_id": 1,
        "name": _display_name(row["source_dataset_name"]),
        "source_url": _source_url(row["source_dataset_name"]),
        "source_dataset_name": row["source_dataset_name"],
        "task_type": row["task_type"],
        "data_purpose": _data_purpose(row["task_type"]),
        "data_format": "Parquet",
        "query_engine": "DuckDB",
        "description": _description_for_source(row["source_dataset_name"]),
        "source_label": row["source_label"],
        "record_count": row["record_count"],
        "registration_date": row["registration_date"],
        "last_updated_date": row["last_updated_date"],
        "created_at": row["registration_date"],
        "gate_status_numeric": row["gate_status_numeric"],
        "quality_status": _quality_status(row["gate_status_numeric"]),
        "quality_score": quality_score,
        "quality_label": _quality_label(quality_score),
        "category": _category_for_task(row["task_type"]),
    }


def _quality_summary(
    quality_metrics: list[dict[str, Any]],
    schema_profile: list[dict[str, Any]],
    task_type: str,
    quality_status: str,
) -> dict[str, Any]:
    metrics = {row["metric_name"]: row["metric_value"] for row in quality_metrics}
    required_empty_count = int(metrics.get("records.empty_required_field_count", 0))
    duplicate_count = int(metrics.get("records.duplicate_exact_count", 0))
    pii_match_count = int(metrics.get("pii.fake_test_match_count", 0))
    total_null_values = sum(int(row.get("null_count", 0)) for row in schema_profile)
    fields_with_nulls = sum(1 for row in schema_profile if int(row.get("null_count", 0)) > 0)
    required_fields = _required_fields_for_task(task_type)
    quality_score = _quality_score_from_values(
        records_total=float(metrics.get("records.total", 0)),
        required_empty_count=required_empty_count,
        duplicate_count=duplicate_count,
        pii_match_count=pii_match_count,
        profile_available=bool(schema_profile),
    )
    return {
        "status": quality_status,
        "score": quality_score,
        "score_label": _quality_label(quality_score),
        "score_explanation": (
            "The score is a 1-100 weighted data-quality score for this dataset version. "
            "Required-field completeness has the highest weight, followed by duplicate rate, "
            "safe PII scanner matches, and whether schema/profile coverage exists."
        ),
        "framework": "Custom expectation-style checks inspired by Great Expectations, Soda, dbt tests, and data contract validation.",
        "meaning": (
            "The quality score summarizes whether the dataset is usable for its stated purpose. "
            "The detailed checks below show the underlying required-field, null, duplicate, token, and PII signals."
        ),
        "procedure": [
            "Normalize raw source records into the shared dataset_records schema.",
            "Profile every normalized field for non-null, null, empty, distinct, and length statistics.",
            "Apply required-field checks based on data_purpose.",
            "Detect exact duplicate records with content_hash.",
            "Compute rough token statistics for input and target text.",
            "Run the safe regex PII scanner on fake/test patterns only.",
            "Calculate a 1-100 score from the weighted checks.",
        ],
        "score_components": [
            {
                "name": "Required-field completeness",
                "weight": 60,
                "description": "Penalizes missing fields required for this dataset purpose.",
            },
            {
                "name": "Exact duplicate rate",
                "weight": 15,
                "description": "Penalizes repeated normalized examples based on content_hash.",
            },
            {
                "name": "Safe PII scan",
                "weight": 15,
                "description": "Penalizes fake/test PII-pattern matches found by the MVP scanner.",
            },
            {
                "name": "Schema/profile coverage",
                "weight": 10,
                "description": "Rewards having generated field-level schema and null profiles.",
            },
        ],
        "required_fields": required_fields,
        "null_value_policy": (
            "Nulls are counted field by field. A null fails the gate only when the field is required "
            "for this dataset purpose; optional fields can be null when they do not apply to the dataset type."
        ),
        "total_null_values": total_null_values,
        "fields_with_nulls": fields_with_nulls,
        "checks": [
            {
                "name": "Required fields",
                "status": "ok" if required_empty_count == 0 else "review",
                "metric_name": "records.empty_required_field_count",
                "metric_value": required_empty_count,
                "description": f"Required fields for this purpose: {', '.join(required_fields)}.",
            },
            {
                "name": "Purpose-aware null profile",
                "status": "measured",
                "metric_name": "schema.null_values.total",
                "metric_value": total_null_values,
                "description": f"{fields_with_nulls} profiled fields contain null or empty values.",
            },
            {
                "name": "Exact duplicates",
                "status": "review" if duplicate_count else "ok",
                "metric_name": "records.duplicate_exact_count",
                "metric_value": duplicate_count,
                "description": "Duplicates are counted by normalized content_hash.",
            },
            {
                "name": "Safe PII pattern scan",
                "status": "review" if pii_match_count else "ok",
                "metric_name": "pii.fake_test_match_count",
                "metric_value": pii_match_count,
                "description": "The MVP scanner uses safe fake/test regex patterns, not real sensitive examples.",
            },
        ],
    }


def _quality_score_from_values(
    records_total: float,
    required_empty_count: float,
    duplicate_count: float,
    pii_match_count: float,
    profile_available: bool,
) -> int:
    if records_total <= 0:
        return 1

    required_score = 60 * max(0.0, 1 - (required_empty_count / records_total))
    duplicate_score = 15 * max(0.0, 1 - (duplicate_count / records_total))
    pii_score = 15 * max(0.0, 1 - (pii_match_count / records_total))
    profile_score = 10 if profile_available else 0
    return max(1, min(100, round(required_score + duplicate_score + pii_score + profile_score)))


def _quality_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Needs review"
    return "Blocked"


def _required_fields_for_task(task_type: str) -> list[str]:
    return {
        "instruction_tuning": ["input_text", "target_text"],
        "preference_pair": ["input_text", "chosen_text", "rejected_text"],
        "summarization": ["input_text", "target_text"],
        "question_answering": ["context", "question", "target_text"],
        "coding_eval": ["input_text", "target_text"],
    }.get(task_type, ["input_text", "target_text"])
