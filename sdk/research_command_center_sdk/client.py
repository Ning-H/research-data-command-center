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

    def get_dataset(self, dataset_id: str) -> dict[str, Any]:
        return self._get(f"/datasets/{dataset_id}")

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
