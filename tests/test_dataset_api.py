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
        sample_record = records_response.json()["items"][0]

        schema_response = client.get("/datasets/1/versions/1/schema")
        assert schema_response.status_code == 200
        schema_fields = [field["field_name"] for field in schema_response.json()["items"]]
        assert schema_fields == list(sample_record.keys())
        assert schema_response.json()["items"][0]["field_name"] == "record_id"
        assert schema_response.json()["items"][0]["field_type"] == "integer"
        assert "target_text" in schema_fields
        assert "response_text" in schema_fields
        assert "metadata_json" not in schema_fields
        assert "prompt_messages_json" not in schema_fields
        assert "dataset_id" not in schema_fields
        assert "dataset_version_id" not in schema_fields

        versions_response = client.get("/datasets/1/versions")
        assert versions_response.status_code == 200
        assert versions_response.json()["items"][0]["dataset_version_id"] == 1

        version_detail_response = client.get("/datasets/1/versions/1")
        assert version_detail_response.status_code == 200
        version_detail = version_detail_response.json()
        assert version_detail["dataset_id"] == 1
        assert version_detail["dataset_version_id"] == 1
        assert len(version_detail["sample_records"]) == 5
        assert [field["field_name"] for field in version_detail["schema_profile"]] == list(
            version_detail["sample_records"][0].keys()
        )
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


def test_dataset_registration_and_version_creation_api(tmp_path: Path) -> None:
    def override_repository() -> DatasetRepository:
        return DatasetRepository(
            duckdb_path=tmp_path / "duckdb" / "research_command_center.duckdb",
            storage_root=tmp_path,
        )

    app.dependency_overrides[get_dataset_repository] = override_repository
    app.dependency_overrides[get_dataset_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        register_response = client.post(
            "/datasets/register",
            json={
                "name": "Registered Python Study Notes",
                "description": "Small registered dataset for backend API tests.",
                "source_url": "s3://research-data/raw/python-study-notes.jsonl",
                "source_dataset_name": "registered/python-study-notes",
                "source_label": "GENERATED_REAL",
                "task_type": "study_guide_generation",
                "data_purpose": "Training data for structured technical study-guide generation",
                "category": "Study-guide generation",
                "records": [
                    {
                        "instruction": "Explain binary search for Python learners.",
                        "response": "Binary search finds a target or boundary in sorted data.",
                    },
                    {
                        "instruction": "Explain sliding window for Python learners.",
                        "response": "Sliding window tracks a contiguous range efficiently.",
                    },
                ],
            },
        )
        assert register_response.status_code == 200
        registered = register_response.json()
        assert registered["dataset_id"] == 9
        assert registered["dataset_version_id"] == 1
        assert registered["name"] == "Registered Python Study Notes"
        assert registered["source_url"] == "s3://research-data/raw/python-study-notes.jsonl"
        assert registered["record_count"] == 2

        version_response = client.post(
            "/datasets/9/versions",
            json={
                "version_notes": "Add a failure-correction example.",
                "records": [
                    {
                        "instruction": "Explain dynamic programming with common mistakes.",
                        "response": "Dynamic programming stores overlapping subproblem results and needs a clear state definition.",
                    }
                ],
            },
        )
        assert version_response.status_code == 200
        created_version = version_response.json()
        assert created_version["dataset_id"] == 9
        assert created_version["dataset_version_id"] == 2
        assert created_version["record_count"] == 1

        versions_response = client.get("/datasets/9/versions")
        assert versions_response.status_code == 200
        versions = versions_response.json()["items"]
        assert [version["dataset_version_id"] for version in versions] == [1, 2]

        latest_response = client.get("/datasets/9")
        assert latest_response.status_code == 200
        assert latest_response.json()["dataset_version_id"] == 2

        first_version_response = client.get("/datasets/9/versions/1")
        assert first_version_response.status_code == 200
        first_version = first_version_response.json()
        assert first_version["dataset_version_id"] == 1
        assert len(first_version["sample_records"]) == 2
        assert first_version["sample_records"][0]["record_id"] == 1
    finally:
        app.dependency_overrides.clear()


def test_dataset_draft_validate_publish_lifecycle_api(tmp_path: Path) -> None:
    def override_repository() -> DatasetRepository:
        return DatasetRepository(
            duckdb_path=tmp_path / "duckdb" / "research_command_center.duckdb",
            storage_root=tmp_path,
        )

    app.dependency_overrides[get_dataset_repository] = override_repository
    app.dependency_overrides[get_dataset_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        register_response = client.post(
            "/datasets/register",
            json={
                "name": "Draft Lifecycle Dataset",
                "description": "Dataset used to test draft validation and publishing.",
                "source_dataset_name": "registered/draft-lifecycle",
                "source_label": "GENERATED_REAL",
                "task_type": "instruction_tuning",
                "records": [
                    {
                        "instruction": "Explain a validation split.",
                        "response": "A validation split estimates behavior before final evaluation.",
                    }
                ],
            },
        )
        assert register_response.status_code == 200
        dataset_id = register_response.json()["dataset_id"]

        draft_response = client.post(
            f"/datasets/{dataset_id}/versions/draft",
            json={
                "version_notes": "Stage a second training-data snapshot.",
                "records": [
                    {
                        "instruction": "Explain immutable dataset versions.",
                        "response": "Published versions cannot be changed after training or eval lineage uses them.",
                    }
                ],
            },
        )
        assert draft_response.status_code == 200
        draft = draft_response.json()
        assert draft["draft_id"] == "draft_1"
        assert draft["status"] == "draft"
        assert draft["record_count"] == 1
        assert draft["job"]["records_written"] == 1

        append_response = client.post(
            f"/datasets/{dataset_id}/versions/draft_1/append",
            json={
                "records": [
                    {
                        "instruction": "Explain draft staging.",
                        "response": "Draft staging lets researchers change records before publish.",
                    }
                ],
            },
        )
        assert append_response.status_code == 200
        assert append_response.json()["record_count"] == 2

        validate_response = client.post(f"/datasets/{dataset_id}/versions/draft_1/validate", json={})
        assert validate_response.status_code == 200
        validation = validate_response.json()["validation"]
        assert validation["status"] == "ready"
        assert validation["record_count"] == 2
        assert validation["quality_issues"] == []

        publish_response = client.post(
            f"/datasets/{dataset_id}/versions/draft_1/publish",
            json={"version_notes": "Publish staged records after local validation."},
        )
        assert publish_response.status_code == 200
        published = publish_response.json()
        assert published["dataset_version"]["dataset_id"] == dataset_id
        assert published["dataset_version"]["dataset_version_id"] == 2
        assert published["draft"]["status"] == "published"
        assert published["job"]["records_written"] == 2

        version_response = client.get(f"/datasets/{dataset_id}/versions/2")
        assert version_response.status_code == 200
        version = version_response.json()
        assert version["dataset_version_id"] == 2
        assert len(version["sample_records"]) == 2

        post_publish_append_response = client.post(
            f"/datasets/{dataset_id}/versions/draft_1/append",
            json={
                "records": [
                    {
                        "instruction": "Try to mutate a published draft.",
                        "response": "This should fail.",
                    }
                ],
            },
        )
        assert post_publish_append_response.status_code == 400

        job_id = published["job"]["dataset_ingestion_job_id"]
        job_response = client.get(f"/dataset-ingestion-jobs/{job_id}")
        assert job_response.status_code == 200
        assert job_response.json()["source_dataset_name"] == "registered/draft-lifecycle"
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
