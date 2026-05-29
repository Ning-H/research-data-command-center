from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from research_command_center_contract.enums import SourcePriority
from research_command_center_contract.tables import ANALYTICAL_TABLES

DOLLY_DATASET_ID = "ds_databricks_dolly_15k"
DOLLY_DATASET_NAME = "Databricks Dolly 15k"
DOLLY_SOURCE_DATASET_NAME = "databricks/databricks-dolly-15k"
DOLLY_SOURCE_URL = (
    "https://huggingface.co/datasets/databricks/databricks-dolly-15k/resolve/main/"
    "databricks-dolly-15k.jsonl"
)
DOLLY_TASK_TYPE = "instruction_tuning"
DOLLY_CATEGORY = "instruction"
DEFAULT_OWNER_USER_ID = "user_demo_owner"
DEFAULT_VERSION = "v1"
SCANNER_NAME = "regex_safe_test_scanner"
SCANNER_VERSION = "0.1.0"
PARQUET_COLUMNS = {table.name: list(table.columns) for table in ANALYTICAL_TABLES}


@dataclass(frozen=True)
class IngestionResult:
    dataset_id: str
    dataset_version_id: str
    record_count: int
    raw_uri: str
    parquet_uri: str
    duckdb_path: str


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def short_hash(value: str, length: int = 10) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def content_hash_for_fields(*values: Any) -> str:
    joined = "\n".join("" if value is None else str(value) for value in values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def build_dataset_version_id(
    source_dataset_name: str = DOLLY_SOURCE_DATASET_NAME,
    version: str = DEFAULT_VERSION,
) -> str:
    digest = short_hash(f"{source_dataset_name}:{version}")
    return f"dsv_databricks_dolly_15k_raw_{version}_{digest}"


def build_record_id(
    dataset_version_id: str,
    source_split: str,
    source_row_id: str,
    content_hash: str,
) -> str:
    return f"rec_{dataset_version_id}_{source_split}_{source_row_id}_{content_hash[:10]}"


def normalize_dolly_record(
    source_row: dict[str, Any],
    source_row_id: int,
    dataset_version_id: str,
    created_at: str,
    source_split: str = "train",
) -> dict[str, Any]:
    instruction = _clean_text(source_row.get("instruction"))
    context = _clean_text(source_row.get("context"))
    response = _clean_text(source_row.get("response"))
    category = _clean_text(source_row.get("category")) or DOLLY_CATEGORY
    content_hash = content_hash_for_fields(instruction, context, response, category)

    return {
        "record_id": build_record_id(
            dataset_version_id=dataset_version_id,
            source_split=source_split,
            source_row_id=str(source_row_id),
            content_hash=content_hash,
        ),
        "dataset_id": DOLLY_DATASET_ID,
        "dataset_version_id": dataset_version_id,
        "source_dataset_name": DOLLY_SOURCE_DATASET_NAME,
        "source_split": source_split,
        "source_row_id": str(source_row_id),
        "category": category,
        "task_type": DOLLY_TASK_TYPE,
        "input_text": "\n\n".join(part for part in (instruction, context) if part),
        "instruction": instruction,
        "context": context,
        "question": "",
        "chosen_text": "",
        "rejected_text": "",
        "target_text": response,
        "response_text": response,
        "prompt_messages_json": json.dumps(
            [{"role": "user", "content": "\n\n".join(part for part in (instruction, context) if part)}],
            ensure_ascii=True,
        ),
        "metadata_json": json.dumps({"dolly_category": category}, ensure_ascii=True),
        "content_hash": content_hash,
        "source_label": SourcePriority.PUBLIC_REAL.value,
        "created_at": created_at,
    }


def load_jsonl_records(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if limit is not None and len(records) >= limit:
                break
            records.append(json.loads(line))
    return records


def download_source(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:
        destination.write_bytes(response.read())


def build_schema_profile(records: list[dict[str, Any]], dataset_version_id: str, created_at: str) -> list[dict[str, Any]]:
    if not records:
        return []

    profile_rows: list[dict[str, Any]] = []
    for field_name in records[0].keys():
        values = [record.get(field_name) for record in records]
        string_values = ["" if value is None else str(value) for value in values]
        populated_values = [value for value in string_values if value != ""]
        lengths = [len(value) for value in populated_values]
        examples = populated_values[:3]
        profile_rows.append(
            {
                "dataset_version_id": dataset_version_id,
                "field_name": field_name,
                "field_type": "string",
                "non_null_count": len(populated_values),
                "null_count": len(values) - len(populated_values),
                "empty_count": sum(1 for value in string_values if value == ""),
                "distinct_count": len(set(populated_values)),
                "min_length": min(lengths) if lengths else 0,
                "max_length": max(lengths) if lengths else 0,
                "mean_length": sum(lengths) / len(lengths) if lengths else 0.0,
                "example_values_json": json.dumps(examples, ensure_ascii=True),
                "created_at": created_at,
            }
        )
    return profile_rows


def build_quality_report(records: list[dict[str, Any]], dataset_version_id: str, created_at: str) -> list[dict[str, Any]]:
    duplicate_count = sum(max(count - 1, 0) for count in Counter(record["content_hash"] for record in records).values())
    required_empty_count = sum(
        1
        for record in records
        if not record["instruction"].strip() or not record["response_text"].strip()
    )
    token_totals = [_rough_token_count(record["input_text"]) + _rough_token_count(record["response_text"]) for record in records]
    pii_matches = sum(_safe_pii_match_count(record) for record in records)
    gate_status_numeric = 0 if required_empty_count == 0 else 1

    metrics = {
        "records.total": float(len(records)),
        "records.empty_required_field_count": float(required_empty_count),
        "records.duplicate_exact_count": float(duplicate_count),
        "tokens.mean": float(sum(token_totals) / len(token_totals)) if token_totals else 0.0,
        "tokens.p95": float(_percentile(token_totals, 0.95)) if token_totals else 0.0,
        "pii.fake_test_match_count": float(pii_matches),
        "quality.gate_status_numeric": float(gate_status_numeric),
    }

    return [
        {
            "dataset_version_id": dataset_version_id,
            "timestamp": created_at,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "source_priority": SourcePriority.GENERATED_REAL.value,
        }
        for metric_name, metric_value in metrics.items()
    ]


def build_duplicate_report(records: list[dict[str, Any]], dataset_version_id: str, created_at: str) -> list[dict[str, Any]]:
    record_ids_by_hash: dict[str, list[str]] = defaultdict(list)
    for record in records:
        record_ids_by_hash[record["content_hash"]].append(record["record_id"])

    return [
        {
            "dataset_version_id": dataset_version_id,
            "content_hash": content_hash,
            "duplicate_count": len(record_ids),
            "record_ids_json": json.dumps(record_ids, ensure_ascii=True),
            "created_at": created_at,
        }
        for content_hash, record_ids in record_ids_by_hash.items()
        if len(record_ids) > 1
    ]


def build_token_statistics(records: list[dict[str, Any]], dataset_version_id: str, created_at: str) -> list[dict[str, Any]]:
    return [
        {
            "dataset_version_id": dataset_version_id,
            "record_id": record["record_id"],
            "tokenizer_name": "rough_whitespace_v0",
            "input_token_count": _rough_token_count(record["input_text"]),
            "target_token_count": _rough_token_count(record["response_text"]),
            "total_token_count": _rough_token_count(record["input_text"]) + _rough_token_count(record["response_text"]),
            "created_at": created_at,
        }
        for record in records
    ]


def build_pii_scan_results(records: list[dict[str, Any]], dataset_version_id: str, created_at: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        text = " ".join(
            [
                record["input_text"],
                record["response_text"],
                record["metadata_json"],
            ]
        )
        for pii_type, pattern in _safe_pii_patterns().items():
            match_count = len(re.findall(pattern, text))
            if match_count:
                rows.append(
                    {
                        "dataset_version_id": dataset_version_id,
                        "record_id": record["record_id"],
                        "pii_type": pii_type,
                        "match_count": match_count,
                        "scanner_name": SCANNER_NAME,
                        "scanner_version": SCANNER_VERSION,
                        "created_at": created_at,
                    }
                )
    return rows


def build_lineage_rows(dataset_version_id: str, created_at: str) -> list[dict[str, Any]]:
    return [
        {
            "dataset_id": DOLLY_DATASET_ID,
            "source_dataset_version_id": "",
            "target_dataset_version_id": dataset_version_id,
            "lineage_event_type": "raw_to_normalized",
            "transform_name": "normalize_databricks_dolly_15k",
            "transform_config_uri": "",
            "created_at": created_at,
            "created_by_user_id": DEFAULT_OWNER_USER_ID,
        }
    ]


def build_metadata(dataset_version_id: str, created_at: str, raw_uri: str, parquet_uri: str) -> dict[str, Any]:
    return {
        "dataset": {
            "dataset_id": DOLLY_DATASET_ID,
            "name": DOLLY_DATASET_NAME,
            "description": "Human-written instruction-following dataset used as the first training-data catalog asset.",
            "category": DOLLY_CATEGORY,
            "default_task_type": DOLLY_TASK_TYPE,
            "source_label": SourcePriority.PUBLIC_REAL.value,
            "owner_user_id": DEFAULT_OWNER_USER_ID,
            "created_at": created_at,
            "updated_at": created_at,
        },
        "dataset_version": {
            "dataset_id": DOLLY_DATASET_ID,
            "dataset_version_id": dataset_version_id,
            "name": f"{DOLLY_DATASET_NAME} {DEFAULT_VERSION}",
            "version": DEFAULT_VERSION,
            "status": "published",
            "source_priority": SourcePriority.PUBLIC_REAL.value,
            "raw_uri": raw_uri,
            "parquet_uri": parquet_uri,
            "schema_uri": f"storage/object_store/datasets/{DOLLY_DATASET_ID}/versions/{dataset_version_id}/source_schema.json",
            "parent_dataset_version_id": "",
            "created_at": created_at,
            "created_by_user_id": DEFAULT_OWNER_USER_ID,
        },
    }


def ingest_dolly(storage_root: Path, limit: int | None = None, download: bool = True) -> IngestionResult:
    created_at = utc_now_iso()
    dataset_version_id = build_dataset_version_id()
    ingest_date = created_at[:10]
    raw_path = (
        storage_root
        / "raw"
        / "datasets"
        / DOLLY_DATASET_ID
        / "databricks-dolly-15k"
        / ingest_date
        / "databricks-dolly-15k.jsonl"
    )

    if download or not raw_path.exists():
        download_source(DOLLY_SOURCE_URL, raw_path)

    source_records = load_jsonl_records(raw_path, limit=limit)
    return _write_dolly_outputs(
        storage_root=storage_root,
        source_records=source_records,
        raw_path=raw_path,
        dataset_version_id=dataset_version_id,
        created_at=created_at,
    )


def ingest_dolly_records(
    storage_root: Path,
    source_records: list[dict[str, Any]],
) -> IngestionResult:
    created_at = utc_now_iso()
    dataset_version_id = build_dataset_version_id()
    raw_path = (
        storage_root
        / "raw"
        / "datasets"
        / DOLLY_DATASET_ID
        / "databricks-dolly-15k"
        / created_at[:10]
        / "databricks-dolly-15k.jsonl"
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=True) for record in source_records),
        encoding="utf-8",
    )
    return _write_dolly_outputs(
        storage_root=storage_root,
        source_records=source_records,
        raw_path=raw_path,
        dataset_version_id=dataset_version_id,
        created_at=created_at,
    )


def register_duckdb_views(storage_root: Path, duckdb_path: Path) -> None:
    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(duckdb_path))
    try:
        view_patterns = {
            "dataset_records": storage_root / "parquet" / "dataset_records" / "**" / "*.parquet",
            "dataset_schema_profiles": storage_root / "parquet" / "dataset_schema_profiles" / "**" / "*.parquet",
            "dataset_quality_reports": storage_root / "parquet" / "dataset_quality_reports" / "**" / "*.parquet",
            "dataset_duplicate_reports": storage_root / "parquet" / "dataset_duplicate_reports" / "**" / "*.parquet",
            "dataset_pii_scan_results": storage_root / "parquet" / "dataset_pii_scan_results" / "**" / "*.parquet",
            "dataset_token_statistics": storage_root / "parquet" / "dataset_token_statistics" / "**" / "*.parquet",
            "dataset_lineage": storage_root / "parquet" / "dataset_lineage" / "**" / "*.parquet",
        }
        for view_name, pattern in view_patterns.items():
            escaped_pattern = str(pattern).replace("'", "''")
            hive_partitioning = "false" if view_name == "dataset_lineage" else "true"
            connection.execute(
                f"""
                CREATE OR REPLACE VIEW {view_name} AS
                SELECT * FROM read_parquet('{escaped_pattern}', hive_partitioning = {hive_partitioning}, union_by_name = true)
                """
            )
    finally:
        connection.close()


def _write_dolly_outputs(
    storage_root: Path,
    source_records: list[dict[str, Any]],
    raw_path: Path,
    dataset_version_id: str,
    created_at: str,
) -> IngestionResult:
    normalized_records = [
        normalize_dolly_record(
            source_row=record,
            source_row_id=index,
            dataset_version_id=dataset_version_id,
            created_at=created_at,
        )
        for index, record in enumerate(source_records)
    ]

    records_dir = (
        storage_root
        / "parquet"
        / "dataset_records"
        / f"dataset_id={DOLLY_DATASET_ID}"
        / f"dataset_version_id={dataset_version_id}"
        / "split=train"
    )
    records_path = records_dir / "records.parquet"
    profile_path = _single_table_path(storage_root, "dataset_schema_profiles", dataset_version_id, "profile.parquet")
    quality_path = _single_table_path(storage_root, "dataset_quality_reports", dataset_version_id, "report.parquet")
    duplicates_path = _single_table_path(storage_root, "dataset_duplicate_reports", dataset_version_id, "duplicates.parquet")
    pii_path = _single_table_path(storage_root, "dataset_pii_scan_results", dataset_version_id, "pii.parquet")
    tokens_path = _single_table_path(storage_root, "dataset_token_statistics", dataset_version_id, "tokens.parquet")
    lineage_path = storage_root / "parquet" / "dataset_lineage" / f"dataset_id={DOLLY_DATASET_ID}" / "lineage.parquet"

    _write_parquet(normalized_records, records_path)
    _write_parquet(build_schema_profile(normalized_records, dataset_version_id, created_at), profile_path)
    _write_parquet(build_quality_report(normalized_records, dataset_version_id, created_at), quality_path)
    _write_parquet(build_duplicate_report(normalized_records, dataset_version_id, created_at), duplicates_path)
    _write_parquet(build_pii_scan_results(normalized_records, dataset_version_id, created_at), pii_path)
    _write_parquet(build_token_statistics(normalized_records, dataset_version_id, created_at), tokens_path)
    _write_parquet(build_lineage_rows(dataset_version_id, created_at), lineage_path)

    object_dir = storage_root / "object_store" / "datasets" / DOLLY_DATASET_ID / "versions" / dataset_version_id
    object_dir.mkdir(parents=True, exist_ok=True)
    metadata = build_metadata(
        dataset_version_id=dataset_version_id,
        created_at=created_at,
        raw_uri=str(raw_path),
        parquet_uri=str(records_path),
    )
    _write_json(metadata["dataset_version"], object_dir / "manifest.json")
    _write_json(_source_schema(source_records), object_dir / "source_schema.json")
    _write_json(
        {
            "dataset_id": DOLLY_DATASET_ID,
            "dataset_version_id": dataset_version_id,
            "records_written": len(normalized_records),
            "normalizer": "normalize_dolly_record",
            "created_at": created_at,
        },
        object_dir / "normalization_report.json",
    )
    _write_json({"metrics": build_quality_report(normalized_records, dataset_version_id, created_at)}, object_dir / "quality_summary.json")

    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)

    return IngestionResult(
        dataset_id=DOLLY_DATASET_ID,
        dataset_version_id=dataset_version_id,
        record_count=len(normalized_records),
        raw_uri=str(raw_path),
        parquet_uri=str(records_path),
        duckdb_path=str(duckdb_path),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest Databricks Dolly 15k into the local dataset lake.")
    parser.add_argument("--storage-root", default="storage", type=Path)
    parser.add_argument("--limit", default=None, type=int)
    parser.add_argument("--no-download", action="store_true")
    args = parser.parse_args(argv)

    result = ingest_dolly(
        storage_root=args.storage_root,
        limit=args.limit,
        download=not args.no_download,
    )
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


def _single_table_path(storage_root: Path, table_name: str, dataset_version_id: str, filename: str) -> Path:
    return (
        storage_root
        / "parquet"
        / table_name
        / f"dataset_id={DOLLY_DATASET_ID}"
        / f"dataset_version_id={dataset_version_id}"
        / filename
    )


def _write_parquet(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table_name = next((part for part in path.parts if part in PARQUET_COLUMNS), None)
    columns = PARQUET_COLUMNS.get(table_name, None)
    pd.DataFrame(rows, columns=columns).to_parquet(path, index=False)


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _source_schema(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"fields": []}
    return {
        "fields": [
            {"name": key, "inferred_type": type(value).__name__}
            for key, value in records[0].items()
        ]
    }


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _rough_token_count(text: str) -> int:
    return len([part for part in re.split(r"\s+", text.strip()) if part])


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, int(round((len(sorted_values) - 1) * percentile)))
    return sorted_values[index]


def _safe_pii_patterns() -> dict[str, str]:
    return {
        "fake_email": r"\b[a-zA-Z0-9._%+-]+@example\.(?:com|org|net)\b",
        "fake_phone_555": r"\b555-\d{3}-\d{4}\b",
    }


def _safe_pii_match_count(record: dict[str, Any]) -> int:
    text = " ".join([record["input_text"], record["response_text"], record["metadata_json"]])
    return sum(len(re.findall(pattern, text)) for pattern in _safe_pii_patterns().values())


if __name__ == "__main__":
    raise SystemExit(main())
