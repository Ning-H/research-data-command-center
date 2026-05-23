from pathlib import Path

from fastapi.testclient import TestClient

from app.datasets.api import get_dataset_repository
from app.datasets.api import get_dataset_storage_root
from app.datasets.dolly_ingestion import ingest_dolly_records
from app.datasets.public_ingestions import ingest_samsum_records
from app.datasets.repository import DatasetRepository
from app.main import app
from app.research_programs.lifecycle import register_research_program
from app.research_programs.repository import ResearchProgramRepository


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
        assert catalog_items[0]["quality_score"] == 100
        assert catalog_items[0]["quality_label"] == "Excellent"

        detail_response = client.get("/datasets/1")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["dataset_version_id"] == 1
        assert detail["dataset_id"] == 1
        assert detail["registration_date"] == detail["last_updated_date"]
        assert detail["data_purpose"] == "Training data for instruction tuning"
        assert detail["data_format"] == "Parquet"
        assert detail["query_engine"] == "DuckDB"
        assert "Human-written instruction-following data" in detail["description"]
        assert len(detail["sample_records"]) == 5
        assert {"input_text", "target_text", "question", "chosen_text", "rejected_text"}.issubset(
            detail["sample_records"][0]
        )
        assert detail["sample_records"][0]["record_id"] == 1
        assert "record_storage_key" not in detail["sample_records"][0]
        assert {metric["metric_name"] for metric in detail["quality_metrics"]} >= {
            "records.total",
            "tokens.mean",
        }
        assert detail["quality_score"] == 100
        assert detail["quality_summary"]["score"] == 100
        assert detail["quality_summary"]["score_label"] == "Excellent"
        assert detail["quality_summary"]["score_components"][0]["weight"] == 60
        assert "input_text" in detail["quality_summary"]["required_fields"]
        assert "Nulls are counted" in detail["quality_summary"]["null_value_policy"]
        assert detail["quality_summary"]["checks"][0]["metric_name"] == "records.empty_required_field_count"

        records_response = client.get("/datasets/1/versions/1/records?limit=2")
        assert records_response.status_code == 200
        assert len(records_response.json()["items"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_dataset_access_records_research_program_usage(tmp_path: Path) -> None:
    result = ingest_dolly_records(
        storage_root=tmp_path,
        source_records=[
            {
                "instruction": f"Use dataset example {index}",
                "context": "Program-linking test context.",
                "response": "Program-linking test response.",
                "category": "open_qa",
            }
            for index in range(5)
        ],
    )
    register_research_program(
        storage_root=tmp_path,
        payload={
            "program_name": "Dataset access linking test",
            "status": "active",
            "researcher_names": ["Lena Keys"],
        },
    )

    def override_repository() -> DatasetRepository:
        return DatasetRepository(duckdb_path=Path(result.duckdb_path), storage_root=tmp_path)

    app.dependency_overrides[get_dataset_repository] = override_repository
    app.dependency_overrides[get_dataset_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        access_response = client.post(
            "/datasets/1/versions/1/access",
            json={
                "program_id": 1,
                "access_purpose": "training_export",
                "user_id": "Lena Keys",
            },
        )
        assert access_response.status_code == 200
        access = access_response.json()
        assert access["linked_datasets"] == [{"dataset_id": 1, "dataset_version_id": 1}]

        program = ResearchProgramRepository(
            duckdb_path=Path(result.duckdb_path),
            storage_root=tmp_path,
        ).get_program(1)
        assert program is not None
        assert program["linked_datasets"] == [{"dataset_id": 1, "dataset_version_id": 1}]
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
            "/datasets/3/versions/1/records?q=eval"
        )
        assert records_response.status_code == 200
        records = records_response.json()["items"]
        assert len(records) == 1
        assert records[0]["source_row_id"] == "s1"
    finally:
        app.dependency_overrides.clear()
