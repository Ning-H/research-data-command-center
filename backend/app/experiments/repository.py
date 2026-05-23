from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from app.experiments.lifecycle import register_experiment_duckdb_view


class ExperimentRepository:
    def __init__(self, duckdb_path: Path, storage_root: Path) -> None:
        self.duckdb_path = duckdb_path
        self.storage_root = storage_root
        register_experiment_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)

    def list_experiments(
        self,
        program_id: int | None = None,
        status: str | None = None,
        tag: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._has_table("experiments"):
            return []
        filters: list[str] = []
        params: list[Any] = []
        if program_id is not None:
            filters.append("program_id = ?")
            params.append(int(program_id))
        if status:
            filters.append("status = ?")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = self._query(
            f"""
            SELECT *
            FROM experiments
            {where_clause}
            ORDER BY updated_at DESC, experiment_id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        )
        experiments = [_experiment_row(row) for row in rows]
        if tag:
            normalized_tag = tag.lower()
            experiments = [
                experiment
                for experiment in experiments
                if normalized_tag in {str(item).lower() for item in experiment.get("tags", [])}
            ]
        if q:
            normalized_query = q.lower()
            experiments = [
                experiment
                for experiment in experiments
                if normalized_query in _experiment_search_text(experiment)
            ]
        return experiments

    def get_experiment(self, experiment_id: int) -> dict[str, Any] | None:
        if not self._has_table("experiments"):
            return None
        rows = self._query("SELECT * FROM experiments WHERE experiment_id = ?", [int(experiment_id)])
        if not rows:
            return None
        experiment = _experiment_row(rows[0])
        return {
            **experiment,
            "ui_workflow": {
                "can_update_from_ui": True,
                "supported_actions": [
                    "edit_experiment_overview",
                    "update_status",
                    "edit_variants",
                    "attach_dataset_versions",
                    "attach_training_runs",
                    "append_decision_notes",
                ],
            },
        }

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


def _experiment_row(row: dict[str, Any]) -> dict[str, Any]:
    experiment = {key: value for key, value in row.items() if not key.endswith("_json")}
    return {
        **experiment,
        "tags": _json_list(row.get("tags_json")),
        "variants": _json_list(row.get("variants_json")),
        "linked_dataset_ids": _json_list(row.get("linked_dataset_ids_json")),
        "linked_dataset_versions": _json_list(row.get("linked_dataset_versions_json")),
        "linked_run_ids": _json_list(row.get("linked_run_ids_json")),
        "linked_model_version_ids": _json_list(row.get("linked_model_version_ids_json")),
    }


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return list(json.loads(str(value)))


def _experiment_search_text(experiment: dict[str, Any]) -> str:
    values = [
        experiment.get("experiment_name"),
        experiment.get("experiment_description"),
        experiment.get("research_question"),
        experiment.get("hypothesis"),
        experiment.get("experiment_type"),
        experiment.get("current_focus"),
        experiment.get("data_strategy"),
        experiment.get("evaluation_plan"),
        experiment.get("decision_notes"),
        " ".join(str(tag) for tag in experiment.get("tags", [])),
    ]
    return " ".join(str(value or "").lower() for value in values)
