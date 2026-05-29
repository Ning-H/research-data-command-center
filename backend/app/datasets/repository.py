from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import duckdb


API_RECORD_FIELDS: tuple[str, ...] = (
    "record_id",
    "source_split",
    "source_row_id",
    "category",
    "task_type",
    "input_text",
    "instruction",
    "context",
    "question",
    "chosen_text",
    "rejected_text",
    "target_text",
    "response_text",
    "content_hash",
)


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
        return [_dataset_summary_from_row(row, self.storage_root) for row in rows]

    def get_dataset(self, dataset_id: str) -> dict[str, Any] | None:
        versions = self.list_dataset_versions(dataset_id)
        if not versions:
            return None
        latest_version = max(versions, key=lambda version: int(version["dataset_version_id"]))
        return self.get_dataset_version(dataset_id, str(latest_version["dataset_version_id"]))

    def list_dataset_versions(self, dataset_id: str) -> list[dict[str, Any]]:
        if not self.duckdb_path.exists():
            return []
        storage_dataset_id = _storage_dataset_id_for_display_id(dataset_id)
        rows = self._query(
            """
            WITH versions AS (
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
                WHERE dataset_id = ?
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
                versions.dataset_id,
                versions.dataset_version_id,
                versions.source_dataset_name,
                versions.task_type,
                versions.source_label,
                versions.record_count,
                versions.registration_date,
                versions.last_updated_date,
                COALESCE(quality.gate_status_numeric, 1) AS gate_status_numeric,
                COALESCE(quality.records_total, versions.record_count) AS records_total,
                COALESCE(quality.required_empty_count, 0) AS required_empty_count,
                COALESCE(quality.duplicate_count, 0) AS duplicate_count,
                COALESCE(quality.pii_match_count, 0) AS pii_match_count
            FROM versions
            LEFT JOIN quality USING (dataset_version_id)
            ORDER BY TRY_CAST(regexp_extract(versions.dataset_version_id, 'v([0-9]+)$', 1) AS INTEGER), versions.dataset_version_id
            """,
            [storage_dataset_id],
        )
        versions = [_dataset_summary_from_row(row, self.storage_root) for row in rows]
        return sorted(versions, key=lambda version: int(version["dataset_version_id"]))

    def get_dataset_version(self, dataset_id: str, dataset_version_id: str) -> dict[str, Any] | None:
        versions = [
            version
            for version in self.list_dataset_versions(dataset_id)
            if str(version["dataset_version_id"]) == str(dataset_version_id)
        ]
        if not versions:
            return None
        dataset = versions[0]
        storage_dataset_id = _storage_dataset_id_for_display_id(dataset["dataset_id"])
        storage_dataset_version_id = _storage_version_id_for_display_id(
            dataset["dataset_id"],
            dataset["dataset_version_id"],
        )
        quality_metrics = self._get_quality_metrics_by_storage_version(storage_dataset_version_id)
        full_schema_profile = self._get_schema_profile_by_storage_version(storage_dataset_version_id)
        schema_profile = _api_record_schema_profile(
            storage_schema_profile=full_schema_profile,
            record_count=int(dataset["record_count"]),
        )
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
        storage_schema_profile = self._get_schema_profile_by_storage_version(storage_dataset_version_id)
        schema_profile = _api_record_schema_profile(
            storage_schema_profile=storage_schema_profile,
            record_count=self._record_count_by_storage_version(storage_dataset_version_id),
        )
        return schema_profile[:limit] if limit is not None else schema_profile

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

    def get_experiment_handoff(
        self,
        dataset_id: str,
        dataset_version_id: str,
    ) -> dict[str, Any] | None:
        dataset_version = self.get_dataset_version(dataset_id, dataset_version_id)
        if dataset_version is None:
            return None

        public_dataset_id = int(dataset_id)
        public_dataset_version_id = int(dataset_version_id)
        iteration_manifest = _read_dataset_iteration_manifest(
            storage_root=self.storage_root,
            dataset_id=public_dataset_id,
            dataset_version_id=public_dataset_version_id,
        )
        candidates = self._included_candidates_for_dataset_version(
            dataset_id=public_dataset_id,
            dataset_version_id=public_dataset_version_id,
            candidate_ids=[
                int(candidate_id)
                for candidate_id in iteration_manifest.get("included_candidate_ids", [])
            ],
        )
        failure_type_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}
        source_model_version_ids: set[int] = set()
        source_eval_run_ids: set[int] = set()
        source_failure_ids: set[int] = set()
        for candidate in candidates:
            failure_type = str(candidate.get("failure_type") or "unknown")
            severity = str(candidate.get("severity") or "unknown")
            failure_type_counts[failure_type] = failure_type_counts.get(failure_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            source_model_version_ids.add(int(candidate.get("source_model_version_id") or 0))
            source_eval_run_ids.add(int(candidate.get("source_eval_run_id") or 0))
            source_failure_ids.add(int(candidate.get("eval_failure_id") or 0))

        ready_for_next_experiment = bool(candidates)
        dominant_failure_type = _dominant_count_value(failure_type_counts)
        return {
            "dataset_version": {
                "dataset_id": public_dataset_id,
                "dataset_version_id": public_dataset_version_id,
                "name": dataset_version["name"],
                "record_count": dataset_version["record_count"],
                "quality_score": dataset_version["quality_score"],
                "quality_label": dataset_version["quality_label"],
                "parent_dataset_version_id": int(
                    iteration_manifest.get("parent_dataset_version_id") or 0
                ),
            },
            "iteration_manifest": iteration_manifest,
            "source_candidates": candidates,
            "failure_summary": {
                "candidate_count": len(candidates),
                "source_eval_failure_ids": sorted(value for value in source_failure_ids if value),
                "source_eval_run_ids": sorted(value for value in source_eval_run_ids if value),
                "source_model_version_ids": sorted(value for value in source_model_version_ids if value),
                "by_failure_type": _sorted_count_dict(failure_type_counts),
                "by_severity": _sorted_count_dict(severity_counts),
            },
            "recommended_next_experiment": {
                "ready": ready_for_next_experiment,
                "program_id": int(candidates[0].get("program_id") or 0) if candidates else 0,
                "experiment_id": int(candidates[0].get("experiment_id") or 0) if candidates else 0,
                "variant_name": f"failure_replay_dataset_v{public_dataset_version_id}",
                "linked_datasets": [
                    {
                        "dataset_id": public_dataset_id,
                        "dataset_version_id": public_dataset_version_id,
                    }
                ],
                "research_intent": (
                    "Run the next study-material experiment with the candidate-derived "
                    f"dataset version and check whether {dominant_failure_type or 'captured failures'} improve."
                ),
                "evaluation_requirement": (
                    "Compare against the same eval suite and rubric metrics used by the source "
                    "model versions before promoting the next checkpoint."
                ),
            },
        }

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
                "target_dataset_version_id": _display_version_id_for_storage_version_id(
                    row["target_dataset_version_id"]
                ),
                "source_label": "generated pipeline"
                if str(row["dataset_id"]).startswith("ds_python_algorithm_study_guides")
                else "public source",
                "lineage_event_type": row["lineage_event_type"],
                "transform_name": row["transform_name"],
                "transform_config_uri": row["transform_config_uri"],
                "created_at": row["created_at"],
                "created_by_user_id": row["created_by_user_id"],
            }
            for row in rows
        ]

    def _record_count_by_storage_version(self, storage_dataset_version_id: str) -> int:
        rows = self._query(
            """
            SELECT COUNT(*) AS record_count
            FROM dataset_records
            WHERE dataset_version_id = ?
            """,
            [storage_dataset_version_id],
        )
        return int(rows[0]["record_count"] or 0) if rows else 0

    def _included_candidates_for_dataset_version(
        self,
        dataset_id: int,
        dataset_version_id: int,
        candidate_ids: list[int],
    ) -> list[dict[str, Any]]:
        if not self._has_table("dataset_candidates"):
            return []
        filters = ["dc.included_dataset_id = ?", "dc.included_dataset_version_id = ?"]
        params: list[Any] = [dataset_id, dataset_version_id]
        if candidate_ids:
            placeholders = ", ".join("?" for _ in candidate_ids)
            filters.append(f"dc.dataset_candidate_id IN ({placeholders})")
            params.extend(candidate_ids)

        joins = ""
        select_fields = [
            "dc.dataset_candidate_id",
            "dc.eval_failure_id",
            "dc.source_eval_run_id",
            "dc.source_eval_output_id",
            "dc.source_model_version_id",
            "dc.program_id",
            "dc.experiment_id",
            "dc.target_dataset_id",
            "dc.failure_type",
            "dc.status AS candidate_status",
            "dc.proposed_input_text",
            "dc.proposed_target_text",
            "dc.review_notes",
            "dc.created_at",
            "dc.reviewed_at",
            "dc.included_dataset_id",
            "dc.included_dataset_version_id",
            "dc.included_at",
        ]
        if self._has_table("eval_failures"):
            joins += " LEFT JOIN eval_failures ef ON dc.eval_failure_id = ef.eval_failure_id"
            select_fields.extend(
                [
                    "ef.severity",
                    "ef.status AS failure_status",
                    "ef.failure_reason",
                    "ef.dataset_id AS source_dataset_id",
                    "ef.dataset_version_id AS source_dataset_version_id",
                ]
            )
        else:
            select_fields.extend(
                [
                    "'' AS severity",
                    "'' AS failure_status",
                    "'' AS failure_reason",
                    "0 AS source_dataset_id",
                    "0 AS source_dataset_version_id",
                ]
            )
        if self._has_table("eval_outputs"):
            joins += " LEFT JOIN eval_outputs eo ON dc.source_eval_output_id = eo.eval_output_id"
            select_fields.extend(["eo.prompt_text", "eo.output_text"])
        else:
            select_fields.extend(["'' AS prompt_text", "'' AS output_text"])
        if self._has_table("model_versions"):
            joins += " LEFT JOIN model_versions mv ON dc.source_model_version_id = mv.model_version_id"
            select_fields.extend(["mv.model_name", "mv.model_version_name"])
        else:
            select_fields.extend(["'' AS model_name", "'' AS model_version_name"])

        return self._query(
            f"""
            SELECT {", ".join(select_fields)}
            FROM dataset_candidates dc
            {joins}
            WHERE {" AND ".join(filters)}
            ORDER BY dc.dataset_candidate_id
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

    def _query(self, query: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        connection = duckdb.connect(str(self.duckdb_path), read_only=True)
        try:
            result = connection.execute(query, params or [])
            columns = [column[0] for column in result.description]
            return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
        finally:
            connection.close()


def _api_record_schema_profile(
    storage_schema_profile: list[dict[str, Any]],
    record_count: int,
) -> list[dict[str, Any]]:
    rows_by_field = {row["field_name"]: row for row in storage_schema_profile}
    schema: list[dict[str, Any]] = []
    for field_name in API_RECORD_FIELDS:
        row = dict(rows_by_field.get(field_name) or _empty_schema_row(field_name, record_count))
        if field_name == "record_id":
            row.update(
                {
                    "field_type": "integer",
                    "non_null_count": record_count,
                    "null_count": 0,
                    "empty_count": 0,
                    "distinct_count": record_count,
                    "min_length": 1 if record_count else 0,
                    "max_length": len(str(record_count)) if record_count else 0,
                    "mean_length": 0.0,
                }
            )
        schema.append({key: row[key] for key in _schema_response_keys()})
    return schema


def _empty_schema_row(field_name: str, record_count: int) -> dict[str, Any]:
    return {
        "field_name": field_name,
        "field_type": "string",
        "non_null_count": 0,
        "null_count": record_count,
        "empty_count": record_count,
        "distinct_count": 0,
        "min_length": 0,
        "max_length": 0,
        "mean_length": 0.0,
    }


def _schema_response_keys() -> tuple[str, ...]:
    return (
        "field_name",
        "field_type",
        "non_null_count",
        "null_count",
        "empty_count",
        "distinct_count",
        "min_length",
        "max_length",
        "mean_length",
    )


def _display_name(source_dataset_name: str) -> str:
    return {
        "databricks/databricks-dolly-15k": "Databricks Dolly 15k",
        "Anthropic/hh-rlhf": "Anthropic HH-RLHF",
        "knkarthick/samsum": "SAMSum Dialogue Summarization",
        "allenai/squad": "SQuAD Question Answering",
        "openai/openai_humaneval": "OpenAI HumanEval",
        "generated/python-algorithm-study-guides/control": "Python Algorithm Study-Guide Control Data",
        "generated/python-algorithm-study-guides/outline-first": "Python Algorithm Study-Guide Outline-First Data",
        "generated/python-algorithm-study-guides/failure-corrections": "Python Algorithm Study-Guide Failure-Correction Data",
    }.get(source_dataset_name, source_dataset_name)


def _dataset_display_id(source_dataset_name: str) -> int:
    return {
        "databricks/databricks-dolly-15k": 1,
        "Anthropic/hh-rlhf": 2,
        "knkarthick/samsum": 3,
        "allenai/squad": 4,
        "openai/openai_humaneval": 5,
        "generated/python-algorithm-study-guides/control": 6,
        "generated/python-algorithm-study-guides/outline-first": 7,
        "generated/python-algorithm-study-guides/failure-corrections": 8,
    }.get(source_dataset_name, 0)


def _dataset_display_id_for_storage_id(dataset_id: str) -> int:
    fixed_id = {
        "ds_databricks_dolly_15k": 1,
        "ds_anthropic_hh_rlhf": 2,
        "ds_samsum": 3,
        "ds_squad": 4,
        "ds_openai_humaneval": 5,
        "ds_python_algorithm_study_guides_control": 6,
        "ds_python_algorithm_study_guides_outline_first": 7,
        "ds_python_algorithm_study_guides_failure_corrections": 8,
    }.get(dataset_id)
    if fixed_id is not None:
        return fixed_id
    match = re.fullmatch(r"ds_dataset_(\d+)", dataset_id)
    return int(match.group(1)) if match else 0


def _storage_dataset_id_for_display_id(dataset_id: str | int) -> str:
    fixed_id = {
        "1": "ds_databricks_dolly_15k",
        "2": "ds_anthropic_hh_rlhf",
        "3": "ds_samsum",
        "4": "ds_squad",
        "5": "ds_openai_humaneval",
        "6": "ds_python_algorithm_study_guides_control",
        "7": "ds_python_algorithm_study_guides_outline_first",
        "8": "ds_python_algorithm_study_guides_failure_corrections",
    }.get(str(dataset_id))
    if fixed_id is not None:
        return fixed_id
    return f"ds_dataset_{int(dataset_id)}"


def _storage_version_id_for_display_id(dataset_id: str | int, dataset_version_id: str | int) -> str:
    study_guide_versions = {
        ("6", "1"): "dsv_python_algorithm_study_guides_control_v1",
        ("7", "1"): "dsv_python_algorithm_study_guides_outline_first_v1",
        ("8", "1"): "dsv_python_algorithm_study_guides_failure_corrections_v1",
    }
    fixed_study_guide_version = study_guide_versions.get((str(dataset_id), str(dataset_version_id)))
    if fixed_study_guide_version is not None:
        return fixed_study_guide_version
    if str(dataset_version_id) != "1":
        return f"dsv_dataset_{int(dataset_id)}_v{int(dataset_version_id)}"
    fixed_version = {
        "1": "dsv_databricks_dolly_15k_raw_v1_b66c4cf8e4",
        "2": "dsv_anthropic_hh_rlhf_raw_v1_7b57e8e5e3",
        "3": "dsv_samsum_raw_v1_89e5308a7f",
        "4": "dsv_squad_raw_v1_825c43a962",
        "5": "dsv_openai_humaneval_raw_v1_527d4f2ddd",
    }.get(str(dataset_id))
    return fixed_version or f"dsv_dataset_{int(dataset_id)}_v1"


def _display_version_id_for_storage_version_id(storage_dataset_version_id: str) -> int:
    fixed_version = {
        "dsv_python_algorithm_study_guides_control_v1": 1,
        "dsv_python_algorithm_study_guides_outline_first_v1": 1,
        "dsv_python_algorithm_study_guides_failure_corrections_v1": 1,
    }.get(storage_dataset_version_id)
    if fixed_version is not None:
        return fixed_version
    match = re.fullmatch(r"dsv_dataset_\d+_v(\d+)", storage_dataset_version_id)
    if match:
        return int(match.group(1))
    return 1


def _source_url(source_dataset_name: str) -> str:
    if source_dataset_name.startswith("generated/python-algorithm-study-guides"):
        storage_id = _storage_dataset_id_for_display_id(_dataset_display_id(source_dataset_name))
        return f"storage/object_store/datasets/{storage_id}"
    return f"https://huggingface.co/datasets/{source_dataset_name}"


def _category_for_task(task_type: str) -> str:
    return {
        "instruction_tuning": "Instruction tuning",
        "preference_pair": "Preference / safety",
        "summarization": "Summarization",
        "question_answering": "Question answering",
        "coding_eval": "Coding eval",
        "study_guide_generation": "Study-guide generation",
    }.get(task_type, task_type.replace("_", " ").title())


def _data_purpose(task_type: str) -> str:
    return {
        "instruction_tuning": "Training data for instruction tuning",
        "preference_pair": "Preference and safety alignment data",
        "summarization": "Summarization training or evaluation data",
        "question_answering": "Question-answering evaluation data",
        "coding_eval": "Coding evaluation benchmark data",
        "study_guide_generation": "Training data for structured technical study-guide generation",
    }.get(task_type, task_type.replace("_", " ").title())


def _description_for_source(source_dataset_name: str) -> str:
    return {
        "databricks/databricks-dolly-15k": "Human-written instruction-following data used to bootstrap the dataset catalog and training-data workflow.",
        "Anthropic/hh-rlhf": "Chosen/rejected assistant responses for preference, helpfulness, and safety research workflows.",
        "knkarthick/samsum": "Dialogue-summary pairs for summarization training and evaluation workflows.",
        "allenai/squad": "Context/question/answer records for QA evaluation and optional training workflows.",
        "openai/openai_humaneval": "Python coding benchmark tasks for model evaluation and checkpoint comparison workflows.",
        "generated/python-algorithm-study-guides/control": "Baseline study-guide examples for the control arm of the Python algorithm study-material experiment.",
        "generated/python-algorithm-study-guides/outline-first": "Outline-first study-guide examples for the first test arm of the Python algorithm study-material experiment.",
        "generated/python-algorithm-study-guides/failure-corrections": "Failure-correction study-guide examples for the second test arm of the Python algorithm study-material experiment.",
    }.get(source_dataset_name, "Versioned public dataset normalized into the shared research-data schema.")


def _quality_status(gate_status_numeric: float | int | None) -> str:
    return "ready" if gate_status_numeric == 0 else "review"


def _dataset_summary_from_row(row: dict[str, Any], storage_root: Path) -> dict[str, Any]:
    manifest = _read_dataset_manifest(
        storage_root=storage_root,
        storage_dataset_id=row["dataset_id"],
        storage_dataset_version_id=row["dataset_version_id"],
    )
    dataset_id = int(manifest.get("public_dataset_id") or _dataset_display_id_for_storage_id(row["dataset_id"]))
    dataset_version_id = int(
        manifest.get("public_dataset_version_id")
        or _display_version_id_for_storage_version_id(row["dataset_version_id"])
    )
    is_raw = manifest.get("asset_kind") == "raw"
    quality_score = _quality_score_from_values(
        records_total=float(row["records_total"] or row["record_count"] or 0),
        required_empty_count=float(row["required_empty_count"] or 0),
        duplicate_count=float(row["duplicate_count"] or 0),
        pii_match_count=float(row["pii_match_count"] or 0),
        profile_available=True,
    )
    summary = {
        "dataset_id": dataset_id or _dataset_display_id(row["source_dataset_name"]),
        "dataset_version_id": dataset_version_id,
        "name": manifest.get("display_name") or _display_name(row["source_dataset_name"]),
        "source_url": manifest.get("source_url") or _source_url(row["source_dataset_name"]),
        "source_dataset_name": row["source_dataset_name"],
        "task_type": row["task_type"],
        "data_purpose": manifest.get("data_purpose") or _data_purpose(row["task_type"]),
        "data_format": manifest.get("data_format") or "Parquet",
        "query_engine": manifest.get("query_engine") or "DuckDB",
        "description": manifest.get("description") or _description_for_source(row["source_dataset_name"]),
        "source_label": row["source_label"],
        "record_count": row["record_count"],
        "registration_date": row["registration_date"],
        "last_updated_date": row["last_updated_date"],
        "created_at": row["registration_date"],
        "gate_status_numeric": row["gate_status_numeric"],
        "quality_status": _quality_status(row["gate_status_numeric"]),
        "quality_score": quality_score,
        "quality_label": _quality_label(quality_score),
        "category": manifest.get("category") or _category_for_task(row["task_type"]),
        "asset_kind": "raw" if is_raw else "structured",
        "original_filename": str(manifest.get("original_filename") or ""),
        "file_size_bytes": int(manifest.get("file_size_bytes") or 0),
        "content_type": str(manifest.get("content_type") or ""),
        "raw_object_uri": str(manifest.get("raw_object_uri") or ""),
    }
    if is_raw:
        summary.update(
            {
                "record_count": 0,
                "quality_status": "raw",
                "quality_score": 0,
                "quality_label": "Unprocessed",
            }
        )
    return summary


def _read_dataset_manifest(
    storage_root: Path,
    storage_dataset_id: str,
    storage_dataset_version_id: str,
) -> dict[str, Any]:
    path = storage_root / "object_store" / "datasets" / storage_dataset_id / "versions" / storage_dataset_version_id / "manifest.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_dataset_iteration_manifest(
    storage_root: Path,
    dataset_id: int,
    dataset_version_id: int,
) -> dict[str, Any]:
    path = (
        storage_root
        / "object_store"
        / "dataset_iterations"
        / f"dataset_id={dataset_id}"
        / f"dataset_version_id={dataset_version_id}"
        / "iteration_manifest.json"
    )
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _dominant_count_value(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    return max(counts.items(), key=lambda item: (item[1], item[0]))[0]


def _sorted_count_dict(counts: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


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
    return max(1, min(100, int(required_score + duplicate_score + pii_score + profile_score)))


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
        "study_guide_generation": ["input_text", "target_text"],
    }.get(task_type, ["input_text", "target_text"])
