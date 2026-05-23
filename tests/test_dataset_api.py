from pathlib import Path

from fastapi.testclient import TestClient

from app.datasets.api import get_dataset_repository
from app.datasets.dolly_ingestion import ingest_dolly_records
from app.datasets.public_ingestions import ingest_samsum_records
from app.datasets.repository import DatasetRepository
from app.main import app


def test_dataset_catalog_and_detail_api(tmp_path: Path) -> None:
    source_records = [
        {
            "instruction": f"Write example {index}",
            "context": "Use research platform language.",
            "response": f"Example {index} response.",
            "category": "open_qa",
        }
        for index in range(5)
    ]
    result = ingest_dolly_records(storage_root=tmp_path, source_records=source_records)

    def override_repository() -> DatasetRepository:
        return DatasetRepository(duckdb_path=Path(result.duckdb_path), storage_root=tmp_path)

    app.dependency_overrides[get_dataset_repository] = override_repository
    try:
        client = TestClient(app)
        catalog_response = client.get("/datasets")
        assert catalog_response.status_code == 200
        catalog_items = catalog_response.json()["items"]
        assert len(catalog_items) == 1
        assert catalog_items[0]["name"] == "Databricks Dolly 15k"
        assert catalog_items[0]["record_count"] == 5

        detail_response = client.get(f"/datasets/{result.dataset_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["dataset_version_id"] == result.dataset_version_id
        assert detail["dataset_id"] == result.dataset_id
        assert len(detail["sample_records"]) == 5
        assert {"input_text", "target_text", "question", "chosen_text", "rejected_text"}.issubset(
            detail["sample_records"][0]
        )
        assert detail["sample_records"][0]["record_display_id"] == 1
        assert "record_storage_key" in detail["sample_records"][0]
        assert {metric["metric_name"] for metric in detail["quality_metrics"]} >= {
            "records.total",
            "tokens.mean",
        }

        records_response = client.get(
            f"/datasets/{result.dataset_id}/versions/{result.dataset_version_id}/records?limit=2"
        )
        assert records_response.status_code == 200
        assert len(records_response.json()["items"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_dataset_api_filters_catalog_and_searches_records(tmp_path: Path) -> None:
    result = ingest_samsum_records(
        storage_root=tmp_path,
        source_records=[
            {
                "id": "s1",
                "dialogue": "Researcher: Did the eval finish?\nPlatform: The summarization eval passed.",
                "summary": "The summarization eval passed.",
            },
            {
                "id": "s2",
                "dialogue": "Researcher: Did training finish?\nPlatform: The run is still active.",
                "summary": "The training run is still active.",
            },
        ],
    )

    def override_repository() -> DatasetRepository:
        return DatasetRepository(duckdb_path=Path(result.duckdb_path), storage_root=tmp_path)

    app.dependency_overrides[get_dataset_repository] = override_repository
    try:
        client = TestClient(app)
        catalog_response = client.get("/datasets?q=samsum&task_type=summarization")
        assert catalog_response.status_code == 200
        catalog_items = catalog_response.json()["items"]
        assert len(catalog_items) == 1
        assert catalog_items[0]["name"] == "SAMSum Dialogue Summarization"

        records_response = client.get(
            f"/datasets/{result.dataset_id}/versions/{result.dataset_version_id}/records?q=eval"
        )
        assert records_response.status_code == 200
        records = records_response.json()["items"]
        assert len(records) == 1
        assert records[0]["source_row_id"] == "s1"
    finally:
        app.dependency_overrides.clear()
