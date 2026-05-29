from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


class EvaluationRepository:
    def __init__(self, duckdb_path: Path, storage_root: Path) -> None:
        self.duckdb_path = duckdb_path
        self.storage_root = storage_root

    def list_eval_suites(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if not self._has_table("eval_suites"):
            return []
        rows = self._query(
            """
            SELECT *
            FROM eval_suites
            ORDER BY created_at DESC, eval_suite_id DESC
            LIMIT ? OFFSET ?
            """,
            [limit, offset],
        )
        return [self._suite_row(row) for row in rows]

    def get_eval_suite(self, eval_suite_id: int) -> dict[str, Any] | None:
        if not self._has_table("eval_suites"):
            return None
        rows = self._query("SELECT * FROM eval_suites WHERE eval_suite_id = ?", [eval_suite_id])
        if not rows:
            return None
        suite = self._suite_row(rows[0])
        suite["cases"] = self.list_eval_cases(eval_suite_id)
        return suite

    def list_eval_cases(self, eval_suite_id: int) -> list[dict[str, Any]]:
        if not self._has_table("eval_cases"):
            return []
        rows = self._query(
            """
            SELECT *
            FROM eval_cases
            WHERE eval_suite_id = ?
            ORDER BY eval_case_id
            """,
            [eval_suite_id],
        )
        return [self._case_row(row) for row in rows]

    def list_eval_runs(
        self,
        program_id: int | None = None,
        experiment_id: int | None = None,
        eval_suite_id: int | None = None,
        model_version_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._has_table("eval_runs"):
            return []
        filters: list[str] = []
        params: list[Any] = []
        if program_id is not None:
            filters.append("program_id = ?")
            params.append(int(program_id))
        if experiment_id is not None:
            filters.append("experiment_id = ?")
            params.append(int(experiment_id))
        if eval_suite_id is not None:
            filters.append("eval_suite_id = ?")
            params.append(int(eval_suite_id))
        if model_version_id is not None:
            filters.append("model_version_id = ?")
            params.append(int(model_version_id))
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = self._query(
            f"""
            SELECT *
            FROM eval_runs
            {where_clause}
            ORDER BY ended_at DESC, eval_run_id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        )
        return [self._run_row(row) for row in rows]

    def get_eval_run(self, eval_run_id: int) -> dict[str, Any] | None:
        if not self._has_table("eval_runs"):
            return None
        rows = self._query("SELECT * FROM eval_runs WHERE eval_run_id = ?", [eval_run_id])
        if not rows:
            return None
        run = self._run_row(rows[0])
        run["outputs"] = self.list_eval_outputs(eval_run_id)
        run["failures"] = self.list_eval_failures(eval_run_id=eval_run_id)
        return run

    def list_eval_outputs(self, eval_run_id: int) -> list[dict[str, Any]]:
        if not self._has_table("eval_outputs"):
            return []
        rows = self._query(
            """
            SELECT *
            FROM eval_outputs
            WHERE eval_run_id = ?
            ORDER BY eval_output_id
            """,
            [eval_run_id],
        )
        return [self._output_row(row) for row in rows]

    def list_eval_failures(
        self,
        program_id: int | None = None,
        experiment_id: int | None = None,
        eval_run_id: int | None = None,
        model_version_id: int | None = None,
        dataset_id: int | None = None,
        dataset_version_id: int | None = None,
        failure_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self._has_table("eval_failures"):
            return []
        filters: list[str] = []
        params: list[Any] = []
        if program_id is not None:
            filters.append("er.program_id = ?")
            params.append(int(program_id))
        if experiment_id is not None:
            filters.append("er.experiment_id = ?")
            params.append(int(experiment_id))
        if eval_run_id is not None:
            filters.append("ef.eval_run_id = ?")
            params.append(int(eval_run_id))
        if model_version_id is not None:
            filters.append("ef.model_version_id = ?")
            params.append(int(model_version_id))
        if dataset_id is not None:
            filters.append("ef.dataset_id = ?")
            params.append(int(dataset_id))
        if dataset_version_id is not None:
            filters.append("ef.dataset_version_id = ?")
            params.append(int(dataset_version_id))
        if failure_type:
            filters.append("ef.failure_type = ?")
            params.append(failure_type)
        if severity:
            filters.append("ef.severity = ?")
            params.append(severity)
        if status:
            filters.append("ef.status = ?")
            params.append(status)
        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        candidate_select = "COALESCE(dc.candidate_count, 0) AS dataset_candidate_count"
        candidate_join = """
            LEFT JOIN (
                SELECT eval_failure_id, COUNT(*) AS candidate_count
                FROM dataset_candidates
                GROUP BY eval_failure_id
            ) dc ON ef.eval_failure_id = dc.eval_failure_id
        """
        if not self._has_table("dataset_candidates"):
            candidate_select = "0 AS dataset_candidate_count"
            candidate_join = ""
        rows = self._query(
            f"""
            SELECT
                ef.*,
                er.program_id,
                er.experiment_id,
                er.checkpoint_id,
                er.run_id,
                eo.prompt_text,
                eo.output_text,
                eo.score,
                ec.case_name,
                mv.model_name,
                mv.model_version_name,
                {candidate_select}
            FROM eval_failures ef
            LEFT JOIN eval_runs er ON ef.eval_run_id = er.eval_run_id
            LEFT JOIN eval_outputs eo ON ef.eval_output_id = eo.eval_output_id
            LEFT JOIN eval_cases ec ON ef.eval_case_id = ec.eval_case_id
            LEFT JOIN model_versions mv ON ef.model_version_id = mv.model_version_id
            {candidate_join}
            {where_clause}
            ORDER BY ef.created_at DESC, ef.eval_failure_id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        )
        return [_failure_row(row) for row in rows]

    def get_eval_failure(self, eval_failure_id: int) -> dict[str, Any] | None:
        if not self._has_table("eval_failures"):
            return None
        candidate_select = "COALESCE(dc.candidate_count, 0) AS dataset_candidate_count"
        candidate_join = """
            LEFT JOIN (
                SELECT eval_failure_id, COUNT(*) AS candidate_count
                FROM dataset_candidates
                GROUP BY eval_failure_id
            ) dc ON ef.eval_failure_id = dc.eval_failure_id
        """
        if not self._has_table("dataset_candidates"):
            candidate_select = "0 AS dataset_candidate_count"
            candidate_join = ""
        rows = self._query(
            """
            SELECT
                ef.*,
                er.program_id,
                er.experiment_id,
                er.checkpoint_id,
                er.run_id,
                eo.prompt_text,
                eo.output_text,
                eo.score,
                eo.scores_json,
                ec.case_name,
                ec.expected_topics_json,
                ec.required_sections_json,
                mv.model_name,
                mv.model_version_name,
                mv.source_run_name,
                mv.source_experiment_name,
                {candidate_select}
            FROM eval_failures ef
            LEFT JOIN eval_runs er ON ef.eval_run_id = er.eval_run_id
            LEFT JOIN eval_outputs eo ON ef.eval_output_id = eo.eval_output_id
            LEFT JOIN eval_cases ec ON ef.eval_case_id = ec.eval_case_id
            LEFT JOIN model_versions mv ON ef.model_version_id = mv.model_version_id
            {candidate_join}
            WHERE ef.eval_failure_id = ?
            LIMIT 1
            """.format(candidate_select=candidate_select, candidate_join=candidate_join),
            [int(eval_failure_id)],
        )
        if not rows:
            return None
        failure = _failure_row(rows[0])
        failure["scores"] = _json_object(rows[0].get("scores_json"))
        failure["expected_topics"] = _json_list(rows[0].get("expected_topics_json"))
        failure["required_sections"] = _json_list(rows[0].get("required_sections_json"))
        failure["lineage"] = _failure_lineage(failure)
        failure["dataset_candidates"] = self._dataset_candidates_for_failure(eval_failure_id)
        return failure

    def evaluation_summary(
        self,
        program_id: int | None = None,
        experiment_id: int | None = None,
        eval_suite_id: int | None = None,
        model_version_id: int | None = None,
    ) -> dict[str, Any]:
        if not self._has_table("eval_runs"):
            return _empty_summary(
                program_id=program_id,
                experiment_id=experiment_id,
                eval_suite_id=eval_suite_id,
                model_version_id=model_version_id,
            )
        run_filters, run_params = _eval_run_filters(
            program_id=program_id,
            experiment_id=experiment_id,
            eval_suite_id=eval_suite_id,
            model_version_id=model_version_id,
            alias="er",
        )
        where_clause = f"WHERE {' AND '.join(run_filters)}" if run_filters else ""
        runs = self._query(
            f"""
            SELECT
                er.*,
                mv.model_name,
                mv.model_version_name,
                mv.source_run_name,
                mv.source_experiment_name
            FROM eval_runs er
            LEFT JOIN model_versions mv ON er.model_version_id = mv.model_version_id
            {where_clause}
            ORDER BY er.ended_at DESC, er.eval_run_id DESC
            """,
            run_params,
        )
        if not runs:
            return _empty_summary(
                program_id=program_id,
                experiment_id=experiment_id,
                eval_suite_id=eval_suite_id,
                model_version_id=model_version_id,
            )

        eval_run_ids = [int(row["eval_run_id"]) for row in runs]
        score_rows = self._score_summary_for_eval_runs(eval_run_ids)
        output_counts = self._counts_for_eval_runs(
            table_name="eval_outputs",
            count_column="eval_output_id",
            eval_run_ids=eval_run_ids,
        )
        failure_counts = self._counts_for_eval_runs(
            table_name="eval_failures",
            count_column="eval_failure_id",
            eval_run_ids=eval_run_ids,
        )
        failure_type_counts = self._failure_type_counts_for_eval_runs(eval_run_ids)

        scores_by_run: dict[int, dict[str, dict[str, float]]] = {}
        metric_values: dict[str, list[dict[str, Any]]] = {}
        for row in score_rows:
            eval_run_id = int(row["eval_run_id"])
            metric_name = str(row["metric_name"])
            score = {
                "mean": round(float(row["mean_score"]), 4),
                "min": round(float(row["min_score"]), 4),
                "max": round(float(row["max_score"]), 4),
            }
            scores_by_run.setdefault(eval_run_id, {})[metric_name] = score
            metric_values.setdefault(metric_name, []).append(
                {
                    **score,
                    "eval_run_id": eval_run_id,
                    "model_version_id": int(row["model_version_id"]),
                }
            )

        summary_runs = []
        for row in runs:
            eval_run_id = int(row["eval_run_id"])
            summary_runs.append(
                {
                    **_run_row_static(row),
                    "model_name": row.get("model_name"),
                    "model_version_name": row.get("model_version_name"),
                    "output_count": int(output_counts.get(eval_run_id, 0)),
                    "failure_count": int(failure_counts.get(eval_run_id, 0)),
                    "failure_types": failure_type_counts.get(eval_run_id, {}),
                    "score_summary": scores_by_run.get(eval_run_id, {}),
                    "lineage_summary": {
                        "dataset_id": row["dataset_id"],
                        "dataset_version_id": row["dataset_version_id"],
                        "run_id": row["run_id"],
                        "checkpoint_id": row["checkpoint_id"],
                        "model_version_id": row["model_version_id"],
                        "eval_run_id": row["eval_run_id"],
                    },
                }
            )

        metric_summary = []
        for metric_name, values in sorted(metric_values.items()):
            best = max(values, key=lambda item: item["mean"])
            metric_summary.append(
                {
                    "metric_name": metric_name,
                    "mean": round(sum(item["mean"] for item in values) / len(values), 4),
                    "min": round(min(item["min"] for item in values), 4),
                    "max": round(max(item["max"] for item in values), 4),
                    "best_eval_run_id": best["eval_run_id"],
                    "best_model_version_id": best["model_version_id"],
                }
            )

        return {
            "filters": {
                "program_id": program_id,
                "experiment_id": experiment_id,
                "eval_suite_id": eval_suite_id,
                "model_version_id": model_version_id,
            },
            "eval_run_count": len(summary_runs),
            "model_version_count": len({int(row["model_version_id"]) for row in runs}),
            "output_count": sum(int(value) for value in output_counts.values()),
            "failure_count": sum(int(value) for value in failure_counts.values()),
            "metric_summary": metric_summary,
            "runs": summary_runs,
        }

    def compare_model_versions(
        self,
        model_version_ids: list[int],
        baseline_model_version_id: int | None = None,
        experiment_id: int | None = None,
        eval_suite_id: int | None = None,
    ) -> dict[str, Any]:
        if not model_version_ids:
            raise ValueError("model_version_ids must contain at least one model_version_id")
        ordered_ids = [int(value) for value in model_version_ids]
        baseline_id = int(baseline_model_version_id or ordered_ids[0])
        placeholders = ", ".join("?" for _ in ordered_ids)
        filters = [f"mv.model_version_id IN ({placeholders})"]
        params: list[Any] = [*ordered_ids]
        if experiment_id is not None:
            filters.append("er.experiment_id = ?")
            params.append(int(experiment_id))
        if eval_suite_id is not None:
            filters.append("er.eval_suite_id = ?")
            params.append(int(eval_suite_id))
        where_clause = f"WHERE {' AND '.join(filters)}"
        failure_join = "LEFT JOIN eval_failures ef ON er.eval_run_id = ef.eval_run_id"
        failure_count = "COUNT(DISTINCT ef.eval_failure_id) AS failure_count"
        if not self._has_table("eval_failures"):
            failure_join = ""
            failure_count = "0 AS failure_count"
        rows = self._query(
            f"""
            SELECT
                mv.model_id,
                mv.model_version_id,
                mv.model_name,
                mv.model_version_name,
                mv.run_id,
                mv.checkpoint_id,
                mv.dataset_id,
                mv.dataset_version_id,
                mv.status AS model_status,
                er.eval_run_id,
                er.eval_suite_id,
                er.experiment_id,
                er.status AS eval_status,
                er.ended_at,
                COUNT(DISTINCT eo.eval_output_id) AS output_count,
                {failure_count}
            FROM model_versions mv
            LEFT JOIN eval_runs er ON mv.model_version_id = er.model_version_id
            LEFT JOIN eval_outputs eo ON er.eval_run_id = eo.eval_run_id
            {failure_join}
            {where_clause}
            GROUP BY
                mv.model_id,
                mv.model_version_id,
                mv.model_name,
                mv.model_version_name,
                mv.run_id,
                mv.checkpoint_id,
                mv.dataset_id,
                mv.dataset_version_id,
                mv.status,
                er.eval_run_id,
                er.eval_suite_id,
                er.experiment_id,
                er.status,
                er.ended_at
            ORDER BY mv.model_version_id
            """,
            params,
        )
        score_rows = self._score_summary_for_model_versions(
            model_version_ids=ordered_ids,
            experiment_id=experiment_id,
            eval_suite_id=eval_suite_id,
        )
        scores_by_model: dict[int, dict[str, float]] = {}
        for row in score_rows:
            scores_by_model.setdefault(int(row["model_version_id"]), {})[str(row["metric_name"])] = round(
                float(row["mean_score"]),
                4,
            )

        baseline_scores = scores_by_model.get(baseline_id, {})
        by_model: dict[int, dict[str, Any]] = {}
        for row in rows:
            model_version_id = int(row["model_version_id"])
            existing = by_model.get(model_version_id)
            if existing is None or (row.get("eval_run_id") and not existing.get("eval_run_id")):
                scores = scores_by_model.get(model_version_id, {})
                by_model[model_version_id] = {
                    "model_id": row["model_id"],
                    "model_version_id": model_version_id,
                    "model_name": row["model_name"],
                    "model_version_name": row["model_version_name"],
                    "run_id": row["run_id"],
                    "checkpoint_id": row["checkpoint_id"],
                    "dataset_id": row["dataset_id"],
                    "dataset_version_id": row["dataset_version_id"],
                    "model_status": row["model_status"],
                    "eval_run_id": row.get("eval_run_id"),
                    "eval_suite_id": row.get("eval_suite_id"),
                    "experiment_id": row.get("experiment_id"),
                    "eval_status": row.get("eval_status"),
                    "output_count": int(row.get("output_count") or 0),
                    "failure_count": int(row.get("failure_count") or 0),
                    "score_summary": scores,
                    "delta_from_baseline": {
                        metric_name: round(metric_value - baseline_scores.get(metric_name, 0.0), 4)
                        for metric_name, metric_value in scores.items()
                    },
                }

        return {
            "baseline_model_version_id": baseline_id,
            "model_version_ids": ordered_ids,
            "filters": {
                "experiment_id": experiment_id,
                "eval_suite_id": eval_suite_id,
            },
            "items": [by_model[model_id] for model_id in ordered_ids if model_id in by_model],
        }

    def failure_summary(
        self,
        program_id: int | None = None,
        experiment_id: int | None = None,
        model_version_id: int | None = None,
        dataset_id: int | None = None,
    ) -> dict[str, Any]:
        failures = self.list_eval_failures(
            program_id=program_id,
            experiment_id=experiment_id,
            model_version_id=model_version_id,
            dataset_id=dataset_id,
            limit=10_000,
        )
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for failure in failures:
            by_type[str(failure["failure_type"])] = by_type.get(str(failure["failure_type"]), 0) + 1
            by_severity[str(failure["severity"])] = by_severity.get(str(failure["severity"]), 0) + 1
            by_status[str(failure["status"])] = by_status.get(str(failure["status"]), 0) + 1
        return {
            "filters": {
                "program_id": program_id,
                "experiment_id": experiment_id,
                "model_version_id": model_version_id,
                "dataset_id": dataset_id,
            },
            "failure_count": len(failures),
            "by_failure_type": _sorted_count_dict(by_type),
            "by_severity": _sorted_count_dict(by_severity),
            "by_status": _sorted_count_dict(by_status),
        }

    def _dataset_candidates_for_failure(self, eval_failure_id: int) -> list[dict[str, Any]]:
        if not self._has_table("dataset_candidates"):
            return []
        return self._query(
            """
            SELECT *
            FROM dataset_candidates
            WHERE eval_failure_id = ?
            ORDER BY created_at DESC, dataset_candidate_id DESC
            """,
            [int(eval_failure_id)],
        )

    def _score_summary_for_eval_runs(self, eval_run_ids: list[int]) -> list[dict[str, Any]]:
        if not eval_run_ids or not self._has_table("eval_scores"):
            return []
        placeholders = ", ".join("?" for _ in eval_run_ids)
        return self._query(
            f"""
            SELECT
                eval_run_id,
                model_version_id,
                metric_name,
                AVG(metric_value) AS mean_score,
                MIN(metric_value) AS min_score,
                MAX(metric_value) AS max_score
            FROM eval_scores
            WHERE eval_run_id IN ({placeholders})
            GROUP BY eval_run_id, model_version_id, metric_name
            ORDER BY eval_run_id, metric_name
            """,
            [*eval_run_ids],
        )

    def _score_summary_for_model_versions(
        self,
        model_version_ids: list[int],
        experiment_id: int | None = None,
        eval_suite_id: int | None = None,
    ) -> list[dict[str, Any]]:
        if not model_version_ids or not self._has_table("eval_scores"):
            return []
        placeholders = ", ".join("?" for _ in model_version_ids)
        filters = [f"es.model_version_id IN ({placeholders})"]
        params: list[Any] = [*model_version_ids]
        if experiment_id is not None:
            filters.append("er.experiment_id = ?")
            params.append(int(experiment_id))
        if eval_suite_id is not None:
            filters.append("er.eval_suite_id = ?")
            params.append(int(eval_suite_id))
        return self._query(
            f"""
            SELECT
                es.model_version_id,
                es.metric_name,
                AVG(es.metric_value) AS mean_score
            FROM eval_scores es
            LEFT JOIN eval_runs er ON es.eval_run_id = er.eval_run_id
            WHERE {' AND '.join(filters)}
            GROUP BY es.model_version_id, es.metric_name
            ORDER BY es.model_version_id, es.metric_name
            """,
            params,
        )

    def _counts_for_eval_runs(
        self,
        table_name: str,
        count_column: str,
        eval_run_ids: list[int],
    ) -> dict[int, int]:
        if not eval_run_ids or not self._has_table(table_name):
            return {}
        placeholders = ", ".join("?" for _ in eval_run_ids)
        rows = self._query(
            f"""
            SELECT eval_run_id, COUNT({count_column}) AS item_count
            FROM {table_name}
            WHERE eval_run_id IN ({placeholders})
            GROUP BY eval_run_id
            """,
            [*eval_run_ids],
        )
        return {int(row["eval_run_id"]): int(row["item_count"]) for row in rows}

    def _failure_type_counts_for_eval_runs(self, eval_run_ids: list[int]) -> dict[int, dict[str, int]]:
        if not eval_run_ids or not self._has_table("eval_failures"):
            return {}
        placeholders = ", ".join("?" for _ in eval_run_ids)
        rows = self._query(
            f"""
            SELECT eval_run_id, failure_type, COUNT(*) AS item_count
            FROM eval_failures
            WHERE eval_run_id IN ({placeholders})
            GROUP BY eval_run_id, failure_type
            ORDER BY eval_run_id, failure_type
            """,
            [*eval_run_ids],
        )
        counts: dict[int, dict[str, int]] = {}
        for row in rows:
            counts.setdefault(int(row["eval_run_id"]), {})[str(row["failure_type"])] = int(row["item_count"])
        return counts

    def _suite_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return dict(row)

    def _case_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "expected_topics": _json_list(row.get("expected_topics_json")),
            "required_sections": _json_list(row.get("required_sections_json")),
            "rubric": _json_object(row.get("rubric_json")),
            "tags": _json_list(row.get("tags_json")),
        }

    def _run_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return _run_row_static(row)

    def _output_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            **row,
            "scores": _json_object(row.get("scores_json")),
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


def _json_list(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return list(json.loads(str(value)))


def _json_object(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    return dict(json.loads(str(value)))


def _eval_run_filters(
    program_id: int | None = None,
    experiment_id: int | None = None,
    eval_suite_id: int | None = None,
    model_version_id: int | None = None,
    alias: str = "eval_runs",
) -> tuple[list[str], list[Any]]:
    filters: list[str] = []
    params: list[Any] = []
    if program_id is not None:
        filters.append(f"{alias}.program_id = ?")
        params.append(int(program_id))
    if experiment_id is not None:
        filters.append(f"{alias}.experiment_id = ?")
        params.append(int(experiment_id))
    if eval_suite_id is not None:
        filters.append(f"{alias}.eval_suite_id = ?")
        params.append(int(eval_suite_id))
    if model_version_id is not None:
        filters.append(f"{alias}.model_version_id = ?")
        params.append(int(model_version_id))
    return filters, params


def _empty_summary(
    program_id: int | None = None,
    experiment_id: int | None = None,
    eval_suite_id: int | None = None,
    model_version_id: int | None = None,
) -> dict[str, Any]:
    return {
        "filters": {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "eval_suite_id": eval_suite_id,
            "model_version_id": model_version_id,
        },
        "eval_run_count": 0,
        "model_version_count": 0,
        "output_count": 0,
        "failure_count": 0,
        "metric_summary": [],
        "runs": [],
    }


def _run_row_static(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "eval_run_id": row["eval_run_id"],
        "eval_suite_id": row["eval_suite_id"],
        "program_id": row["program_id"],
        "experiment_id": row["experiment_id"],
        "model_version_id": row["model_version_id"],
        "run_id": row["run_id"],
        "checkpoint_id": row["checkpoint_id"],
        "dataset_id": row["dataset_id"],
        "dataset_version_id": row["dataset_version_id"],
        "status": row["status"],
        "source_priority": row.get("source_priority"),
        "started_at": row["started_at"],
        "ended_at": row["ended_at"],
        "created_by_user_id": row["created_by_user_id"],
        "evaluator_name": row.get("evaluator_name") or "",
        "evaluator_version": row.get("evaluator_version") or "",
        "eval_job_uri": row.get("eval_job_uri") or "",
        "external_eval_run_id": row.get("external_eval_run_id") or "",
        "git_commit": row.get("git_commit") or "",
        "environment": _json_object(row.get("environment_json")),
        "notes": row.get("notes") or "",
    }


def _failure_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "eval_failure_id": row["eval_failure_id"],
        "eval_run_id": row["eval_run_id"],
        "eval_output_id": row["eval_output_id"],
        "eval_case_id": row["eval_case_id"],
        "model_version_id": row["model_version_id"],
        "dataset_id": row["dataset_id"],
        "dataset_version_id": row["dataset_version_id"],
        "program_id": row.get("program_id"),
        "experiment_id": row.get("experiment_id"),
        "run_id": row.get("run_id"),
        "checkpoint_id": row.get("checkpoint_id"),
        "failure_type": row["failure_type"],
        "severity": row["severity"],
        "failure_reason": row["failure_reason"],
        "evidence_text": row.get("evidence_text", ""),
        "status": row["status"],
        "root_cause": row.get("root_cause", ""),
        "review_notes": row.get("review_notes", ""),
        "reviewed_at": row.get("reviewed_at", ""),
        "reviewed_by_user_id": row.get("reviewed_by_user_id", ""),
        "created_at": row["created_at"],
        "case_name": row.get("case_name"),
        "prompt_text": row.get("prompt_text"),
        "output_text": row.get("output_text"),
        "score": row.get("score"),
        "model_name": row.get("model_name"),
        "model_version_name": row.get("model_version_name"),
        "dataset_candidate_count": int(row.get("dataset_candidate_count") or 0),
    }


def _failure_lineage(failure: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "lineage_step": "dataset_version_to_run",
            "source_type": "dataset_version",
            "source_id": failure["dataset_version_id"],
            "target_type": "run",
            "target_id": failure.get("run_id"),
        },
        {
            "lineage_step": "run_to_checkpoint",
            "source_type": "run",
            "source_id": failure.get("run_id"),
            "target_type": "checkpoint",
            "target_id": failure.get("checkpoint_id"),
        },
        {
            "lineage_step": "checkpoint_to_model_version",
            "source_type": "checkpoint",
            "source_id": failure.get("checkpoint_id"),
            "target_type": "model_version",
            "target_id": failure["model_version_id"],
        },
        {
            "lineage_step": "model_version_to_eval_failure",
            "source_type": "model_version",
            "source_id": failure["model_version_id"],
            "target_type": "eval_failure",
            "target_id": failure["eval_failure_id"],
        },
    ]


def _sorted_count_dict(values: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"value": key, "count": count}
        for key, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))
    ]
