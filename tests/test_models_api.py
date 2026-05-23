from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.api import get_model_repository, get_model_storage_root
from app.models.lifecycle import register_model_duckdb_views
from app.models.repository import ModelRepository
from app.runs.api import get_run_repository, get_run_storage_root
from app.runs.repository import RunRepository


def test_checkpoint_promotion_creates_model_version_with_derived_lineage(tmp_path: Path) -> None:
    from app.datasets.dolly_ingestion import ingest_dolly_records

    ingest_dolly_records(
        storage_root=tmp_path,
        source_records=[
            {
                "instruction": f"Classify model registry example {index}",
                "context": "Synthetic unit-test source row for model promotion validation.",
                "response": "This record exercises checkpoint-to-model registration.",
                "category": "classification" if index % 2 else "open_qa",
            }
            for index in range(40)
        ],
    )

    duckdb_path = tmp_path / "duckdb" / "research_command_center.duckdb"

    def override_run_repository() -> RunRepository:
        return RunRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    def override_model_repository() -> ModelRepository:
        register_model_duckdb_views(storage_root=tmp_path, duckdb_path=duckdb_path)
        return ModelRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    app.dependency_overrides[get_run_repository] = override_run_repository
    app.dependency_overrides[get_run_storage_root] = lambda: tmp_path
    app.dependency_overrides[get_model_repository] = override_model_repository
    app.dependency_overrides[get_model_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        register_response = client.post(
            "/runs/register",
            json={
                "run_name": "model-registry-source-run",
                "dataset_id": 1,
                "dataset_version_id": 1,
                "base_model_name": "pytorch-linear-text-classifier",
                "training_task": "instruction_category_classification",
                "research_intent": "Produce a checkpoint for model registry validation.",
                "owner_user_id": "user_test",
                "training_environment": "local_test_process",
                "artifact_root_uri": "storage/object_store/test/model-source-run",
                "run_config": {"framework": "pytorch", "trainer": "unit_test_trainer"},
            },
        )
        assert register_response.status_code == 200
        run_id = register_response.json()["run_id"]

        event_response = client.post(
            f"/runs/{run_id}/events",
            json={
                "events": [
                    {
                        "timestamp": "2026-05-23T04:00:00Z",
                        "step": 10,
                        "metrics": {
                            "train.loss": 0.82,
                            "train.accuracy": 0.72,
                            "train.tokens_seen": 512,
                        },
                    }
                ]
            },
        )
        assert event_response.status_code == 200

        checkpoint_response = client.post(
            f"/runs/{run_id}/checkpoints",
            json={
                "checkpoints": [
                    {
                        "step": 10,
                        "checkpoint_uri": "storage/object_store/test/model-source-run/checkpoint_step_10.pt",
                        "metrics_snapshot": {"train.loss": 0.82, "train.accuracy": 0.72},
                    }
                ]
            },
        )
        assert checkpoint_response.status_code == 200
        assert client.post(f"/runs/{run_id}/complete", json={"status": "completed"}).status_code == 200

        promotion_response = client.post(
            "/models/register-from-checkpoint",
            json={
                "checkpoint_id": 1001,
                "model_name": "instruction-classifier",
                "model_version_name": "candidate-checkpoint-1001",
                "intended_use": "Evaluate instruction category classification quality.",
                "promotion_reason": "Best checkpoint for the registered dataset in this run.",
                "owner_user_id": "user_test",
            },
        )
        assert promotion_response.status_code == 200
        promoted = promotion_response.json()
        assert promoted["model_id"] == 1
        assert promoted["model_version_id"] == 1
        assert promoted["checkpoint_id"] == 1001
        assert promoted["run_id"] == run_id
        assert promoted["dataset_id"] == 1
        assert promoted["dataset_version_id"] == 1

        registry_response = client.get("/models")
        assert registry_response.status_code == 200
        registry_items = registry_response.json()["items"]
        assert registry_items[0]["model_version_id"] == 1
        assert registry_items[0]["metrics_snapshot"]["train.accuracy"] == 0.72

        detail_response = client.get("/models/1")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["model_name"] == "instruction-classifier"
        assert detail["lineage_summary"] == {
            "dataset_id": 1,
            "dataset_version_id": 1,
            "run_id": run_id,
            "checkpoint_id": 1001,
            "model_version_id": 1,
        }
        assert detail["lineage"][-1]["lineage_step"] == "checkpoint_to_model_version"

        checkpoint_search = client.get(
            "/checkpoints",
            params={"dataset_id": 1, "dataset_version_id": 1, "ranking_metric": "train.accuracy"},
        ).json()["items"]
        assert checkpoint_search[0]["checkpoint_id"] == 1001
        assert checkpoint_search[0]["promotion_status"] == "promoted"
    finally:
        app.dependency_overrides.clear()
