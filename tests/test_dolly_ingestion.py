import json

from app.datasets.dolly_ingestion import (
    DOLLY_DATASET_ID,
    build_duplicate_report,
    build_quality_report,
    build_schema_profile,
    build_token_statistics,
    build_dataset_version_id,
    normalize_dolly_record,
)


def test_normalize_dolly_record_maps_source_fields_to_common_schema() -> None:
    dataset_version_id = build_dataset_version_id()
    record = normalize_dolly_record(
        source_row={
            "instruction": "Write a friendly launch note",
            "context": "The product is for researchers.",
            "response": "Hello research team, the launch is ready.",
            "category": "creative_writing",
        },
        source_row_id=7,
        dataset_version_id=dataset_version_id,
        created_at="2026-05-22T00:00:00Z",
    )

    assert record["dataset_id"] == DOLLY_DATASET_ID
    assert record["dataset_version_id"] == dataset_version_id
    assert record["task_type"] == "instruction_tuning"
    assert record["source_label"] == "PUBLIC_REAL"
    assert record["instruction"] == "Write a friendly launch note"
    assert record["context"] == "The product is for researchers."
    assert record["response_text"] == "Hello research team, the launch is ready."
    assert record["target_text"] == record["response_text"]
    assert json.loads(record["metadata_json"]) == {"dolly_category": "creative_writing"}


def test_quality_report_uses_generated_real_metrics() -> None:
    dataset_version_id = build_dataset_version_id()
    created_at = "2026-05-22T00:00:00Z"
    records = [
        normalize_dolly_record(
            {
                "instruction": "Email user@example.com",
                "context": "",
                "response": "Use fake test addresses only.",
                "category": "brainstorming",
            },
            source_row_id=0,
            dataset_version_id=dataset_version_id,
            created_at=created_at,
        ),
        normalize_dolly_record(
            {
                "instruction": "Email user@example.com",
                "context": "",
                "response": "Use fake test addresses only.",
                "category": "brainstorming",
            },
            source_row_id=1,
            dataset_version_id=dataset_version_id,
            created_at=created_at,
        ),
    ]

    metrics = {row["metric_name"]: row for row in build_quality_report(records, dataset_version_id, created_at)}

    assert metrics["records.total"]["metric_value"] == 2.0
    assert metrics["records.duplicate_exact_count"]["metric_value"] == 1.0
    assert metrics["pii.fake_test_match_count"]["metric_value"] == 2.0
    assert {row["source_priority"] for row in metrics.values()} == {"GENERATED_REAL"}


def test_profile_duplicate_and_token_outputs_are_query_ready() -> None:
    dataset_version_id = build_dataset_version_id()
    created_at = "2026-05-22T00:00:00Z"
    records = [
        normalize_dolly_record(
            {
                "instruction": "Summarize this",
                "context": "Long context",
                "response": "Short summary",
                "category": "summarization",
            },
            source_row_id=0,
            dataset_version_id=dataset_version_id,
            created_at=created_at,
        )
    ]

    profile = build_schema_profile(records, dataset_version_id, created_at)
    duplicates = build_duplicate_report(records, dataset_version_id, created_at)
    token_stats = build_token_statistics(records, dataset_version_id, created_at)

    assert {row["field_name"] for row in profile} >= {"record_id", "instruction", "response_text"}
    assert duplicates == []
    assert token_stats[0]["total_token_count"] > 0
