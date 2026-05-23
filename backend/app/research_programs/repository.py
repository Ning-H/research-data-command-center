from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from app.research_programs.lifecycle import register_research_program_duckdb_view


class ResearchProgramRepository:
    def __init__(self, duckdb_path: Path, storage_root: Path) -> None:
        self.duckdb_path = duckdb_path
        self.storage_root = storage_root
        register_research_program_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)

    def list_programs(
        self,
        status: str | None = None,
        researcher_name: str | None = None,
        tag: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._has_table("research_programs"):
            return []
        filters: list[str] = []
        params: list[Any] = []
        if status:
            filters.append("status = ?")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = self._query(
            f"""
            SELECT *
            FROM research_programs
            {where_clause}
            ORDER BY updated_at DESC, program_id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        )
        programs = [_program_row(row) for row in rows]
        if researcher_name:
            programs = [
                program
                for program in programs
                if researcher_name in program.get("researcher_names", [])
                or researcher_name == program.get("owner_name")
            ]
        if tag:
            normalized_tag = tag.lower()
            programs = [
                program
                for program in programs
                if normalized_tag in {str(item).lower() for item in program.get("tags", [])}
            ]
        if q:
            normalized_query = q.lower()
            programs = [
                program
                for program in programs
                if normalized_query in _program_search_text(program)
            ]
        return programs

    def get_program(self, program_id: int) -> dict[str, Any] | None:
        if not self._has_table("research_programs"):
            return None
        rows = self._query("SELECT * FROM research_programs WHERE program_id = ?", [int(program_id)])
        if not rows:
            return None
        program = _program_row(rows[0])
        return {
            **program,
            "ui_workflow": {
                "can_update_from_ui": True,
                "supported_actions": [
                    "edit_program_overview",
                    "update_status",
                    "change_researchers",
                    "attach_data_assets",
                    "attach_experiments",
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


def _program_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "researcher_names": _json_list(row.get("researcher_names_json")),
        "success_metrics": _json_list(row.get("success_metrics_json")),
        "tags": _json_list(row.get("tags_json")),
        "linked_dataset_ids": _json_list(row.get("linked_dataset_ids_json")),
        "linked_dataset_versions": _json_list(row.get("linked_dataset_versions_json")),
        "linked_experiment_ids": _json_list(row.get("linked_experiment_ids_json")),
        "linked_run_ids": _json_list(row.get("linked_run_ids_json")),
    }


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return list(json.loads(str(value)))


def _program_search_text(program: dict[str, Any]) -> str:
    values = [
        program.get("program_name"),
        program.get("short_name"),
        program.get("program_description"),
        program.get("problem_statement"),
        program.get("initiating_context"),
        program.get("research_goal"),
        program.get("hypothesis"),
        program.get("research_objectives"),
        program.get("research_area"),
        program.get("current_focus"),
        program.get("decision_notes"),
        " ".join(str(tag) for tag in program.get("tags", [])),
    ]
    return " ".join(str(value or "").lower() for value in values)
