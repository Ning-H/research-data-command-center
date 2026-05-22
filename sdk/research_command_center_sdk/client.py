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

    def _get(self, path: str) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(path)
            response.raise_for_status()
            return response.json()
