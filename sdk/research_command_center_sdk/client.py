from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ResearchCommandCenterClient:
    base_url: str = "http://localhost:8000"
    timeout_seconds: float = 10.0

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def contract(self) -> dict[str, Any]:
        return self._get("/contract")

    def list_datasets(self) -> dict[str, Any]:
        return self._get("/datasets")

    def list_research_programs(
        self,
        tag: str | None = None,
        q: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        params = {"tag": tag, "q": q, "status": status}
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/research-programs?{query}")

    def get_research_program(self, program_id: str | int) -> dict[str, Any]:
        return self._get(f"/research-programs/{program_id}")

    def register_research_program(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/research-programs", payload)

    def update_research_program(
        self,
        program_id: str | int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._patch(f"/research-programs/{program_id}", payload)

    def append_research_program_note(
        self,
        program_id: str | int,
        body: str,
        author_name: str | None = None,
    ) -> dict[str, Any]:
        payload = {"body": body}
        if author_name:
            payload["author_name"] = author_name
        return self._post(f"/research-programs/{program_id}/notes", payload)

    def delete_research_program_note(
        self,
        program_id: str | int,
        note_id: str | int,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {"user_id": user_id} if user_id else None
        return self._delete(f"/research-programs/{program_id}/notes/{note_id}", payload)

    def list_experiments(
        self,
        program_id: str | int | None = None,
        tag: str | None = None,
        q: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        params = {"program_id": program_id, "tag": tag, "q": q, "status": status}
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/experiments?{query}")

    def register_experiment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/experiments", payload)

    def get_experiment(self, experiment_id: str | int) -> dict[str, Any]:
        return self._get(f"/experiments/{experiment_id}")

    def update_experiment(
        self,
        experiment_id: str | int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._patch(f"/experiments/{experiment_id}", payload)

    def append_experiment_note(
        self,
        experiment_id: str | int,
        body: str,
        author_name: str | None = None,
    ) -> dict[str, Any]:
        payload = {"body": body}
        if author_name:
            payload["author_name"] = author_name
        return self._post(f"/experiments/{experiment_id}/notes", payload)

    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        return self._get(f"/datasets/{dataset_id}")

    def list_dataset_versions(self, dataset_id: str | int) -> dict[str, Any]:
        return self._get(f"/datasets/{dataset_id}/versions")

    def get_dataset_version(self, dataset_id: str | int, version_id: str | int) -> dict[str, Any]:
        return self._get(f"/datasets/{dataset_id}/versions/{version_id}")

    def register_dataset(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/datasets/register", payload)

    def create_dataset_version(self, dataset_id: str | int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/datasets/{dataset_id}/versions", payload)

    def create_dataset_version_from_candidates(
        self,
        dataset_id: str | int,
        candidate_ids: list[int] | None = None,
        candidate_status: str = "approved",
        version_notes: str | None = None,
        created_by_user_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"candidate_status": candidate_status}
        if candidate_ids is not None:
            payload["candidate_ids"] = candidate_ids
        if version_notes is not None:
            payload["version_notes"] = version_notes
        if created_by_user_id is not None:
            payload["created_by_user_id"] = created_by_user_id
        return self._post(f"/datasets/{dataset_id}/versions/from-candidates", payload)

    def create_dataset_draft(self, dataset_id: str | int, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/datasets/{dataset_id}/versions/draft", payload)

    def append_dataset_draft(
        self,
        dataset_id: str | int,
        draft_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._post(f"/datasets/{dataset_id}/versions/{draft_id}/append", payload)

    def overwrite_dataset_draft(
        self,
        dataset_id: str | int,
        draft_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._post(f"/datasets/{dataset_id}/versions/{draft_id}/overwrite", payload)

    def validate_dataset_draft(
        self,
        dataset_id: str | int,
        draft_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._post(f"/datasets/{dataset_id}/versions/{draft_id}/validate", payload or {})

    def publish_dataset_draft(
        self,
        dataset_id: str | int,
        draft_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._post(f"/datasets/{dataset_id}/versions/{draft_id}/publish", payload or {})

    def get_dataset_ingestion_job(self, job_id: str | int) -> dict[str, Any]:
        return self._get(f"/dataset-ingestion-jobs/{job_id}")

    def search_dataset_records(
        self,
        dataset_id: str,
        version_id: str,
        limit: int = 25,
    ) -> dict[str, Any]:
        return self._get(f"/datasets/{dataset_id}/versions/{version_id}/records?limit={limit}")

    def get_dataset_quality(self, dataset_id: str, version_id: str) -> dict[str, Any]:
        return self._get(f"/datasets/{dataset_id}/versions/{version_id}/quality")

    def trace_dataset_lineage(self, dataset_id: str, version_id: str) -> dict[str, Any]:
        return self._get(f"/datasets/{dataset_id}/versions/{version_id}/lineage")

    def record_dataset_access(
        self,
        program_id: str | int,
        dataset_id: str | int,
        version_id: str | int,
        access_purpose: str = "training_export",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {"program_id": int(program_id), "access_purpose": access_purpose}
        if user_id:
            payload["user_id"] = user_id
        return self._post(f"/datasets/{dataset_id}/versions/{version_id}/access", payload)

    def list_runs(self) -> dict[str, Any]:
        return self._get("/runs")

    def register_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/runs/register", payload)

    def get_run(self, run_id: str | int) -> dict[str, Any]:
        return self._get(f"/runs/{run_id}")

    def append_run_events(self, run_id: str | int, events: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post(f"/runs/{run_id}/events", {"events": events})

    def get_run_metrics(self, run_id: str | int) -> dict[str, Any]:
        return self._get(f"/runs/{run_id}/metrics")

    def get_run_compute(self, run_id: str | int) -> dict[str, Any]:
        return self._get(f"/runs/{run_id}/compute")

    def get_run_checkpoints(self, run_id: str | int) -> dict[str, Any]:
        return self._get(f"/runs/{run_id}/checkpoints")

    def search_checkpoints(
        self,
        dataset_id: str | int | None = None,
        dataset_version_id: str | int | None = None,
        framework: str | None = None,
        trainer: str | None = None,
        ranking_metric: str = "train.accuracy",
        direction: str = "desc",
    ) -> dict[str, Any]:
        params = {
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "framework": framework,
            "trainer": trainer,
            "ranking_metric": ranking_metric,
            "direction": direction,
        }
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/checkpoints?{query}")

    def append_run_checkpoints(
        self,
        run_id: str | int,
        checkpoints: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._post(f"/runs/{run_id}/checkpoints", {"checkpoints": checkpoints})

    def complete_run(self, run_id: str | int, status: str = "completed") -> dict[str, Any]:
        return self._post(f"/runs/{run_id}/complete", {"status": status})

    def trace_run_lineage(self, run_id: str | int) -> dict[str, Any]:
        return self._get(f"/runs/{run_id}/lineage")

    def list_models(self) -> dict[str, Any]:
        return self._get("/models")

    def register_model_from_checkpoint(
        self,
        checkpoint_id: str | int,
        model_name: str,
        model_version_name: str,
        intended_use: str = "",
        promotion_reason: str = "",
        promotion_notes: str = "",
        owner_user_id: str = "user_demo_owner",
    ) -> dict[str, Any]:
        return self._post(
            "/models/register-from-checkpoint",
            {
                "checkpoint_id": int(checkpoint_id),
                "model_name": model_name,
                "model_version_name": model_version_name,
                "intended_use": intended_use,
                "promotion_reason": promotion_reason,
                "promotion_notes": promotion_notes,
                "owner_user_id": owner_user_id,
            },
        )

    def get_model(self, model_version_id: str | int) -> dict[str, Any]:
        return self._get(f"/models/{model_version_id}")

    def trace_model_lineage(self, model_version_id: str | int) -> dict[str, Any]:
        return self._get(f"/models/{model_version_id}/lineage")

    def get_model_evals(self, model_version_id: str | int) -> dict[str, Any]:
        return self._get(f"/models/{model_version_id}/evals")

    def create_eval_suite(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/eval-suites", payload)

    def list_eval_suites(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        query = str(httpx.QueryParams({"limit": limit, "offset": offset}))
        return self._get(f"/eval-suites?{query}")

    def get_eval_suite(self, eval_suite_id: str | int) -> dict[str, Any]:
        return self._get(f"/eval-suites/{eval_suite_id}")

    def submit_eval_run(
        self,
        eval_suite_id: str | int,
        model_version_id: str | int,
        outputs: list[dict[str, Any]],
        program_id: str | int | None = None,
        experiment_id: str | int | None = None,
        scoring_method: str | None = None,
        status: str = "completed",
        evaluator_name: str | None = None,
        evaluator_version: str | None = None,
        eval_job_uri: str | None = None,
        external_eval_run_id: str | None = None,
        git_commit: str | None = None,
        environment: dict[str, Any] | None = None,
        notes: str | None = None,
        created_by_user_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "eval_suite_id": int(eval_suite_id),
            "model_version_id": int(model_version_id),
            "status": status,
            "outputs": outputs,
        }
        optional_values = {
            "program_id": int(program_id) if program_id is not None else None,
            "experiment_id": int(experiment_id) if experiment_id is not None else None,
            "scoring_method": scoring_method,
            "evaluator_name": evaluator_name,
            "evaluator_version": evaluator_version,
            "eval_job_uri": eval_job_uri,
            "external_eval_run_id": external_eval_run_id,
            "git_commit": git_commit,
            "environment": environment,
            "notes": notes,
            "created_by_user_id": created_by_user_id,
        }
        payload.update({key: value for key, value in optional_values.items() if value is not None})
        return self._post("/eval-runs", payload)

    def list_eval_runs(
        self,
        program_id: str | int | None = None,
        experiment_id: str | int | None = None,
        eval_suite_id: str | int | None = None,
        model_version_id: str | int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        params = {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "eval_suite_id": eval_suite_id,
            "model_version_id": model_version_id,
            "limit": limit,
            "offset": offset,
        }
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/eval-runs?{query}")

    def get_eval_run(self, eval_run_id: str | int) -> dict[str, Any]:
        return self._get(f"/eval-runs/{eval_run_id}")

    def compare_models(
        self,
        model_version_ids: list[int],
        baseline_model_version_id: str | int | None = None,
        experiment_id: str | int | None = None,
        eval_suite_id: str | int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model_version_ids": model_version_ids}
        if baseline_model_version_id is not None:
            payload["baseline_model_version_id"] = int(baseline_model_version_id)
        if experiment_id is not None:
            payload["experiment_id"] = int(experiment_id)
        if eval_suite_id is not None:
            payload["eval_suite_id"] = int(eval_suite_id)
        return self._post("/models/compare", payload)

    def get_evaluation_summary(
        self,
        program_id: str | int | None = None,
        experiment_id: str | int | None = None,
        eval_suite_id: str | int | None = None,
        model_version_id: str | int | None = None,
    ) -> dict[str, Any]:
        params = {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "eval_suite_id": eval_suite_id,
            "model_version_id": model_version_id,
        }
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/evaluations/summary?{query}")

    def search_eval_failures(
        self,
        program_id: str | int | None = None,
        experiment_id: str | int | None = None,
        eval_run_id: str | int | None = None,
        model_version_id: str | int | None = None,
        dataset_id: str | int | None = None,
        dataset_version_id: str | int | None = None,
        failure_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "eval_run_id": eval_run_id,
            "model_version_id": model_version_id,
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "failure_type": failure_type,
            "severity": severity,
            "status": status,
        }
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/failure-library?{query}")

    def get_eval_failure(self, eval_failure_id: str | int) -> dict[str, Any]:
        return self._get(f"/failure-library/{eval_failure_id}")

    def create_dataset_candidate_from_failure(
        self,
        eval_failure_id: str | int,
        target_dataset_id: str | int,
        proposed_input_text: str,
        proposed_target_text: str,
        status: str = "proposed",
        created_by_user_id: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "target_dataset_id": int(target_dataset_id),
            "status": status,
            "proposed_input_text": proposed_input_text,
            "proposed_target_text": proposed_target_text,
        }
        if created_by_user_id is not None:
            payload["created_by_user_id"] = created_by_user_id
        return self._post(f"/eval-failures/{eval_failure_id}/dataset-candidate", payload)

    def list_dataset_candidates(
        self,
        program_id: str | int | None = None,
        experiment_id: str | int | None = None,
        target_dataset_id: str | int | None = None,
        failure_type: str | None = None,
        source_model_version_id: str | int | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "target_dataset_id": target_dataset_id,
            "failure_type": failure_type,
            "source_model_version_id": source_model_version_id,
            "status": status,
        }
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/dataset-candidates?{query}")

    def review_dataset_candidate(
        self,
        candidate_id: str | int,
        status: str,
        review_notes: str = "",
        reviewed_by_user_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {"status": status, "review_notes": review_notes}
        if reviewed_by_user_id is not None:
            payload["reviewed_by_user_id"] = reviewed_by_user_id
        return self._patch(f"/dataset-candidates/{candidate_id}", payload)

    def list_dataset_iterations(
        self,
        program_id: str | int | None = None,
        experiment_id: str | int | None = None,
        target_dataset_id: str | int | None = None,
        failure_type: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        params = {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "target_dataset_id": target_dataset_id,
            "failure_type": failure_type,
            "status": status,
        }
        query = str(httpx.QueryParams({key: value for key, value in params.items() if value is not None}))
        return self._get(f"/dataset-iterations?{query}")

    def _get(self, path: str) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(path)
            response.raise_for_status()
            return response.json()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

    def _patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.patch(path, json=payload)
            response.raise_for_status()
            return response.json()

    def _delete(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.request("DELETE", path, json=payload)
            response.raise_for_status()
            return response.json()
