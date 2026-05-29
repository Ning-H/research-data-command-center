from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from app.experiments.lifecycle import register_experiment_duckdb_view


EXPERIMENT_RESPONSE_FIELDS = {
    "experiment_id",
    "program_id",
    "experiment_name",
    "experiment_description",
    "research_question",
    "hypothesis",
    "experiment_type",
    "status",
    "owner_name",
    "evaluation_plan",
    "decision_notes",
    "input_source",
    "created_at",
    "updated_at",
    "created_by_user_id",
    "updated_by_user_id",
}


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
                    "accept_dataset_handoff",
                    "view_next_run_plan",
                    "append_note",
                ],
            },
        }

    def get_next_run_plan(self, experiment_id: int) -> dict[str, Any] | None:
        experiment = self.get_experiment(experiment_id)
        if experiment is None:
            return None

        linked_datasets = experiment.get("linked_datasets", [])
        selected_dataset = _latest_dataset_ref(linked_datasets)
        can_register_run = selected_dataset is not None
        blocking_reasons = [] if can_register_run else ["experiment has no linked dataset version"]
        run_name = _next_run_name(experiment, selected_dataset)
        dataset_id = int(selected_dataset.get("dataset_id") or 0) if selected_dataset else 0
        dataset_version_id = (
            int(selected_dataset.get("dataset_version_id") or 0) if selected_dataset else 0
        )

        return {
            "experiment_id": int(experiment["experiment_id"]),
            "program_id": int(experiment["program_id"]),
            "experiment_name": experiment["experiment_name"],
            "can_register_run": can_register_run,
            "blocking_reasons": blocking_reasons,
            "selected_dataset": selected_dataset,
            "run_registration_payload": {
                "run_name": run_name,
                "program_id": int(experiment["program_id"]),
                "experiment_id": int(experiment["experiment_id"]),
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "base_model_name": "",
                "training_task": experiment.get("experiment_type") or "failure_replay_training",
                "research_intent": (
                    "Train the next candidate using the accepted dataset version, then compare "
                    "against the source evaluation rubric before promotion."
                ),
                "owner_user_id": experiment.get("owner_name") or "user_demo_owner",
                "training_environment": "researcher_managed",
                "artifact_root_uri": (
                    "storage/object_store/runs/"
                    f"experiment_id={int(experiment['experiment_id'])}/{run_name}"
                ),
                "run_config": {
                    "dataset_ref": selected_dataset or {},
                    "evaluation_plan": experiment.get("evaluation_plan") or "",
                    "source": "experiment_next_run_plan",
                },
            },
            "evaluation_requirement": {
                "summary": (
                    "Run the same eval suite and rubric metrics used by the source model versions "
                    "before promoting a new checkpoint."
                ),
                "compare_against": "source_model_versions_from_dataset_handoff",
            },
            "next_actions": [
                "POST /runs/register",
                "POST /runs/{run_id}/events",
                "POST /runs/{run_id}/checkpoints",
                "POST /runs/{run_id}/complete",
                "POST /models/register-from-checkpoint",
                "POST /eval-runs",
                "POST /models/compare",
            ],
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
    experiment = {
        key: value
        for key, value in row.items()
        if key in EXPERIMENT_RESPONSE_FIELDS and not key.endswith("_json")
    }
    return {
        **experiment,
        "tags": _json_list(row.get("tags_json")),
        "variants": _json_list(row.get("variants_json")),
        "notes": _json_list(row.get("notes_json")),
        "linked_datasets": _json_list(row.get("linked_datasets_json")),
        "linked_run_ids": _json_list(row.get("linked_run_ids_json")),
        "linked_model_version_ids": _json_list(row.get("linked_model_version_ids_json")),
    }


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return list(json.loads(str(value)))


def _latest_dataset_ref(linked_datasets: list[Any]) -> dict[str, int] | None:
    refs = [
        {
            "dataset_id": int(item.get("dataset_id") or 0),
            "dataset_version_id": int(item.get("dataset_version_id") or 0),
        }
        for item in linked_datasets
        if isinstance(item, dict)
    ]
    refs = [ref for ref in refs if ref["dataset_id"] and ref["dataset_version_id"]]
    if not refs:
        return None
    return max(refs, key=lambda ref: (ref["dataset_id"], ref["dataset_version_id"]))


def _next_run_name(experiment: dict[str, Any], dataset_ref: dict[str, int] | None) -> str:
    name = str(experiment.get("experiment_name") or f"experiment-{experiment['experiment_id']}")
    slug = "-".join(name.lower().split())
    slug = "".join(character for character in slug if character.isalnum() or character == "-")
    if dataset_ref is None:
        return f"{slug}-next-run"
    return f"{slug}-dataset-v{dataset_ref['dataset_version_id']}"


def _experiment_search_text(experiment: dict[str, Any]) -> str:
    values = [
        experiment.get("experiment_name"),
        experiment.get("experiment_description"),
        experiment.get("research_question"),
        experiment.get("hypothesis"),
        experiment.get("experiment_type"),
        experiment.get("evaluation_plan"),
        experiment.get("decision_notes"),
        " ".join(str(note.get("body", "")) for note in experiment.get("notes", [])),
        " ".join(str(tag) for tag in experiment.get("tags", [])),
    ]
    return " ".join(str(value or "").lower() for value in values)
