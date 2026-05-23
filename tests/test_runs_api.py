from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.runs.api import get_run_repository
from app.runs.ingestion import seed_demo_runs
from app.runs.repository import RunRepository


def test_runs_api_exposes_researcher_submitted_run_data(tmp_path: Path) -> None:
    results = seed_demo_runs(storage_root=tmp_path)

    def override_repository() -> RunRepository:
        return RunRepository(duckdb_path=Path(results[0].duckdb_path), storage_root=tmp_path)

    app.dependency_overrides[get_run_repository] = override_repository
    try:
        client = TestClient(app)
        list_response = client.get("/runs")
        assert list_response.status_code == 200
        runs = list_response.json()["items"]
        assert len(runs) == 3
        assert {run["status"] for run in runs} == {"completed", "failed"}
        assert runs[0]["ingest_source"] == "researcher_sdk_demo"
        assert runs[0]["health_summary"]["health_score"] > 0

        detail_response = client.get("/runs/1")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["dataset_id"] == 1
        assert detail["dataset_version_id"] == 1
        assert detail["raw_ingest_summary"]["source_priority"] == "GENERATED_REAL"
        assert detail["metric_summary"]["final_loss"] < detail["metric_summary"]["initial_loss"]
        assert len(detail["checkpoints"]) == 3
        assert detail["lineage"][0]["source_type"] == "dataset_version"
        assert detail["lineage"][-1]["target_type"] == "checkpoint"

        metrics_response = client.get("/runs/1/metrics")
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()["items"]
        assert {"run_id", "timestamp", "step", "metric_name", "metric_value"}.issubset(metrics[0])
        assert any(metric["metric_name"] == "train.loss" for metric in metrics)

        checkpoints_response = client.get("/runs/1/checkpoints")
        assert checkpoints_response.status_code == 200
        checkpoints = checkpoints_response.json()["items"]
        assert checkpoints[0]["checkpoint_uri"].startswith("s3://research-runs/")
    finally:
        app.dependency_overrides.clear()
