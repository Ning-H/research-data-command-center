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

    def _get(self, path: str) -> dict[str, Any]:
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get(path)
            response.raise_for_status()
            return response.json()
