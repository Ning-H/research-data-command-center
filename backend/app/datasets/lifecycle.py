from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import duckdb

from app.dataset_candidates.lifecycle import mark_candidates_included, register_dataset_candidate_duckdb_view
from research_command_center_contract.enums import SourcePriority

from app.datasets.pipeline import (
    DatasetDefinition,
    build_quality_report,
    build_schema_profile,
    build_record_id,
    clean_text,
    content_hash_for_fields,
    register_duckdb_views,
    utc_now_iso,
    write_dataset_outputs,
    write_raw_jsonl,
    _write_parquet,
)
from app.datasets.repository import (
    DatasetRepository,
    _dataset_display_id_for_storage_id,
    _storage_dataset_id_for_display_id,
)


DEFAULT_CREATED_BY_USER_ID = "user_demo_owner"
DRAFT_STATUS = "draft"
VALIDATED_STATUS = "validated"
PUBLISHED_STATUS = "published"


def register_dataset(
    storage_root: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    records = _records_from_payload(payload)
    public_dataset_id = int(payload.get("dataset_id") or _next_dataset_id(storage_root))
    if public_dataset_id < 9:
        raise ValueError("dataset_id values 1-8 are reserved for the built-in public/demo datasets")
    if _dataset_exists(storage_root, public_dataset_id):
        raise ValueError(f"dataset_id {public_dataset_id} already exists")
    public_dataset_version_id = int(payload.get("dataset_version_id") or 1)
    if public_dataset_version_id != 1:
        raise ValueError("new dataset registration must start with dataset_version_id=1")

    definition = _definition_from_payload(
        payload=payload,
        public_dataset_id=public_dataset_id,
        existing_storage_dataset_id=None,
    )
    return _write_registered_version(
        storage_root=storage_root,
        payload=payload,
        definition=definition,
        public_dataset_id=public_dataset_id,
        public_dataset_version_id=public_dataset_version_id,
        parent_dataset_version_id="",
        records=records,
    )


def register_raw_dataset(
    storage_root: Path,
    *,
    data: bytes,
    filename: str,
    content_type: str | None,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if not data:
        raise ValueError("uploaded file is empty")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")

    public_dataset_id = _next_dataset_id(storage_root)
    public_dataset_version_id = 1
    storage_dataset_id = f"ds_dataset_{public_dataset_id}"
    storage_dataset_version_id = _storage_dataset_version_id(public_dataset_id, public_dataset_version_id)
    created_at = utc_now_iso()
    source_label = _source_label(payload)

    safe_filename = _safe_filename(filename)
    checksum = hashlib.sha256(data).hexdigest()
    raw_path = (
        storage_root
        / "object_store"
        / "datasets"
        / storage_dataset_id
        / "versions"
        / storage_dataset_version_id
        / "raw"
        / safe_filename
    )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(data)

    task_type = str(payload.get("task_type") or "raw_upload").strip()
    metadata = {
        "asset_kind": "raw",
        "original_filename": safe_filename,
        "file_size_bytes": len(data),
        "content_type": content_type or "application/octet-stream",
        "checksum_sha256": checksum,
        "raw_object_uri": str(raw_path),
    }
    placeholder_record = {
        "record_id": build_record_id(storage_dataset_version_id, "raw", "raw", checksum),
        "dataset_id": storage_dataset_id,
        "dataset_version_id": storage_dataset_version_id,
        "source_dataset_name": name,
        "source_split": "raw",
        "source_row_id": "raw",
        "category": str(payload.get("category") or "Raw upload"),
        "task_type": task_type,
        "input_text": "",
        "instruction": "",
        "context": "",
        "question": "",
        "chosen_text": "",
        "rejected_text": "",
        "target_text": "",
        "response_text": "",
        "prompt_messages_json": json.dumps([], ensure_ascii=True),
        "metadata_json": json.dumps(metadata, sort_keys=True, ensure_ascii=True),
        "content_hash": checksum,
        "source_label": source_label,
        "created_at": created_at,
    }
    records_path = (
        storage_root
        / "parquet"
        / "dataset_records"
        / f"dataset_id={storage_dataset_id}"
        / f"dataset_version_id={storage_dataset_version_id}"
        / "split=raw"
        / "records.parquet"
    )
    _write_parquet([placeholder_record], records_path)

    manifest_path = raw_path.parent.parent / "manifest.json"
    manifest = {
        "public_dataset_id": public_dataset_id,
        "public_dataset_version_id": public_dataset_version_id,
        "dataset_id": storage_dataset_id,
        "dataset_version_id": storage_dataset_version_id,
        "display_name": name,
        "description": str(payload.get("description") or ""),
        "category": str(payload.get("category") or "Raw upload"),
        "task_type": task_type,
        "data_purpose": str(payload.get("data_purpose") or "Raw uploaded data asset stored without processing."),
        "data_format": _format_label(safe_filename, content_type),
        "query_engine": "Object store",
        "source_url": str(raw_path),
        "source_priority": source_label,
        "parent_dataset_version_id": "",
        "created_by_user_id": str(payload.get("created_by_user_id") or DEFAULT_CREATED_BY_USER_ID),
        "version_notes": str(payload.get("version_notes") or ""),
        "data_structure": str(payload.get("data_structure") or "unstructured"),
        "asset_kind": "raw",
        "original_filename": safe_filename,
        "file_size_bytes": len(data),
        "content_type": content_type or "application/octet-stream",
        "checksum_sha256": checksum,
        "raw_object_uri": str(raw_path),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)

    detail = _repository(storage_root).get_dataset_version(
        str(public_dataset_id),
        str(public_dataset_version_id),
    )
    if detail is None:
        raise ValueError("raw dataset was written but could not be read back")
    return {**detail, "raw_uri": str(raw_path)}


def _safe_filename(filename: str) -> str:
    base = Path(filename or "").name.strip() or "upload.bin"
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return cleaned or "upload.bin"


def _format_label(filename: str, content_type: str | None) -> str:
    suffix = Path(filename).suffix.lstrip(".").upper()
    if suffix:
        return suffix
    if content_type:
        return content_type
    return "RAW"


def create_dataset_version(
    storage_root: Path,
    dataset_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    repository = _repository(storage_root)
    existing_versions = repository.list_dataset_versions(str(dataset_id))
    if not existing_versions:
        raise ValueError(f"dataset_id {dataset_id} does not exist")

    records = _records_from_payload(payload)
    public_dataset_version_id = int(
        payload.get("dataset_version_id")
        or max(int(version["dataset_version_id"]) for version in existing_versions) + 1
    )
    if any(int(version["dataset_version_id"]) == public_dataset_version_id for version in existing_versions):
        raise ValueError(f"dataset_version_id {public_dataset_version_id} already exists for dataset_id {dataset_id}")

    latest = max(existing_versions, key=lambda version: int(version["dataset_version_id"]))
    definition = _definition_from_payload(
        payload={**latest, **payload},
        public_dataset_id=dataset_id,
        existing_storage_dataset_id=_storage_dataset_id_for_display_id(dataset_id),
    )
    return _write_registered_version(
        storage_root=storage_root,
        payload={**latest, **payload},
        definition=definition,
        public_dataset_id=dataset_id,
        public_dataset_version_id=public_dataset_version_id,
        parent_dataset_version_id=str(payload.get("parent_dataset_version_id") or latest["dataset_version_id"]),
        records=records,
    )


def create_dataset_draft(
    storage_root: Path,
    dataset_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    latest = _latest_dataset_version(storage_root, dataset_id)
    records = _records_from_payload(payload)
    draft_id = str(payload.get("draft_id") or _next_draft_id(storage_root, dataset_id))
    if _draft_path(storage_root, dataset_id, draft_id).exists():
        raise ValueError(f"draft_id {draft_id} already exists for dataset_id {dataset_id}")

    created_at = str(payload.get("created_at") or utc_now_iso())
    draft = {
        "draft_id": draft_id,
        "dataset_id": dataset_id,
        "base_dataset_version_id": int(latest["dataset_version_id"]),
        "status": DRAFT_STATUS,
        "records": records,
        "record_count": len(records),
        "metadata": _draft_metadata_from_payload({**latest, **payload}),
        "validation": None,
        "created_at": created_at,
        "updated_at": created_at,
        "created_by_user_id": str(payload.get("created_by_user_id") or DEFAULT_CREATED_BY_USER_ID),
        "updated_by_user_id": str(payload.get("updated_by_user_id") or payload.get("created_by_user_id") or DEFAULT_CREATED_BY_USER_ID),
    }
    _write_draft(storage_root, dataset_id, draft_id, draft)
    job = _write_ingestion_job(
        storage_root=storage_root,
        dataset_id=dataset_id,
        source_dataset_name=str(draft["metadata"]["source_dataset_name"]),
        source_config={"operation": "create_draft", "draft_id": draft_id},
        status="completed",
        started_at=created_at,
        ended_at=created_at,
        records_seen=len(records),
        records_written=len(records),
        error_message="",
        created_by_user_id=str(draft["created_by_user_id"]),
    )
    return _draft_response(draft, job)


def append_dataset_draft_records(
    storage_root: Path,
    dataset_id: int,
    draft_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    draft = _read_mutable_draft(storage_root, dataset_id, draft_id)
    records = _records_from_payload(payload)
    draft["records"].extend(records)
    draft["record_count"] = len(draft["records"])
    draft["status"] = DRAFT_STATUS
    draft["validation"] = None
    draft["updated_at"] = str(payload.get("updated_at") or utc_now_iso())
    draft["updated_by_user_id"] = str(payload.get("updated_by_user_id") or payload.get("user_id") or DEFAULT_CREATED_BY_USER_ID)
    _write_draft(storage_root, dataset_id, draft_id, draft)
    job = _write_ingestion_job(
        storage_root=storage_root,
        dataset_id=dataset_id,
        source_dataset_name=str(draft["metadata"]["source_dataset_name"]),
        source_config={"operation": "append_draft", "draft_id": draft_id},
        status="completed",
        started_at=str(draft["updated_at"]),
        ended_at=str(draft["updated_at"]),
        records_seen=len(records),
        records_written=len(records),
        error_message="",
        created_by_user_id=str(draft["updated_by_user_id"]),
    )
    return _draft_response(draft, job)


def overwrite_dataset_draft_records(
    storage_root: Path,
    dataset_id: int,
    draft_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    draft = _read_mutable_draft(storage_root, dataset_id, draft_id)
    records = _records_from_payload(payload)
    draft["records"] = records
    draft["record_count"] = len(records)
    draft["status"] = DRAFT_STATUS
    draft["validation"] = None
    draft["updated_at"] = str(payload.get("updated_at") or utc_now_iso())
    draft["updated_by_user_id"] = str(payload.get("updated_by_user_id") or payload.get("user_id") or DEFAULT_CREATED_BY_USER_ID)
    _write_draft(storage_root, dataset_id, draft_id, draft)
    job = _write_ingestion_job(
        storage_root=storage_root,
        dataset_id=dataset_id,
        source_dataset_name=str(draft["metadata"]["source_dataset_name"]),
        source_config={"operation": "overwrite_draft", "draft_id": draft_id},
        status="completed",
        started_at=str(draft["updated_at"]),
        ended_at=str(draft["updated_at"]),
        records_seen=len(records),
        records_written=len(records),
        error_message="",
        created_by_user_id=str(draft["updated_by_user_id"]),
    )
    return _draft_response(draft, job)


def validate_dataset_draft(
    storage_root: Path,
    dataset_id: int,
    draft_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    draft = _read_draft(storage_root, dataset_id, draft_id)
    if draft["status"] == PUBLISHED_STATUS:
        raise ValueError(f"draft_id {draft_id} is already published")
    now = str((payload or {}).get("validated_at") or utc_now_iso())
    definition = _definition_from_payload(
        payload=draft["metadata"],
        public_dataset_id=dataset_id,
        existing_storage_dataset_id=_storage_dataset_id_for_display_id(dataset_id),
    )
    storage_dataset_version_id = f"draft_{dataset_id}_{draft_id}"
    source_label = str(draft["metadata"].get("source_label") or SourcePriority.SYNTHETIC_REALISTIC.value)
    normalized_records = [
        _normalize_registered_record(
            source_row=row,
            source_row_id=index,
            definition=definition,
            dataset_version_id=storage_dataset_version_id,
            source_label=source_label,
            created_at=now,
        )
        for index, row in enumerate(draft["records"], start=1)
    ]
    quality_metrics = build_quality_report(normalized_records, storage_dataset_version_id, now)
    schema_profile = build_schema_profile(normalized_records, storage_dataset_version_id, now)
    issues = _quality_issues_from_metrics(quality_metrics, schema_profile)
    validation = {
        "status": "ready" if not issues else "review",
        "quality_metrics": quality_metrics,
        "schema_profile": schema_profile,
        "quality_issues": issues,
        "record_count": len(normalized_records),
        "validated_at": now,
    }
    draft["status"] = VALIDATED_STATUS
    draft["validation"] = validation
    draft["updated_at"] = now
    draft["updated_by_user_id"] = str((payload or {}).get("updated_by_user_id") or DEFAULT_CREATED_BY_USER_ID)
    _write_draft(storage_root, dataset_id, draft_id, draft)
    _write_quality_issues(storage_root, dataset_id, draft_id, issues)
    job = _write_ingestion_job(
        storage_root=storage_root,
        dataset_id=dataset_id,
        source_dataset_name=str(draft["metadata"]["source_dataset_name"]),
        source_config={"operation": "validate_draft", "draft_id": draft_id},
        status="completed",
        started_at=now,
        ended_at=now,
        records_seen=len(normalized_records),
        records_written=0,
        error_message="",
        created_by_user_id=str(draft["updated_by_user_id"]),
    )
    return {"draft": _draft_response(draft), "validation": validation, "job": job}


def publish_dataset_draft(
    storage_root: Path,
    dataset_id: int,
    draft_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    draft = _read_draft(storage_root, dataset_id, draft_id)
    if draft["status"] == PUBLISHED_STATUS:
        raise ValueError(f"draft_id {draft_id} is already published")
    if not draft.get("validation"):
        validate_dataset_draft(storage_root=storage_root, dataset_id=dataset_id, draft_id=draft_id, payload=payload)
        draft = _read_draft(storage_root, dataset_id, draft_id)
    validation = draft["validation"]
    if validation["status"] != "ready" and not payload.get("allow_publish_with_issues"):
        raise ValueError("draft validation has review issues; pass allow_publish_with_issues=true to publish anyway")

    latest = _latest_dataset_version(storage_root, dataset_id)
    public_dataset_version_id = int(
        payload.get("dataset_version_id") or int(latest["dataset_version_id"]) + 1
    )
    if any(
        int(version["dataset_version_id"]) == public_dataset_version_id
        for version in _repository(storage_root).list_dataset_versions(str(dataset_id))
    ):
        raise ValueError(f"dataset_version_id {public_dataset_version_id} already exists for dataset_id {dataset_id}")
    publish_payload = {
        **draft["metadata"],
        **payload,
        "dataset_version_id": public_dataset_version_id,
        "parent_dataset_version_id": int(draft["base_dataset_version_id"]),
        "records": draft["records"],
        "version_notes": str(payload.get("version_notes") or f"Published from {draft_id}"),
    }
    detail = create_dataset_version(storage_root=storage_root, dataset_id=dataset_id, payload=publish_payload)
    now = str(payload.get("published_at") or utc_now_iso())
    draft["status"] = PUBLISHED_STATUS
    draft["published_dataset_version_id"] = public_dataset_version_id
    draft["published_at"] = now
    draft["updated_at"] = now
    draft["updated_by_user_id"] = str(payload.get("updated_by_user_id") or DEFAULT_CREATED_BY_USER_ID)
    _write_draft(storage_root, dataset_id, draft_id, draft)
    job = _write_ingestion_job(
        storage_root=storage_root,
        dataset_id=dataset_id,
        source_dataset_name=str(draft["metadata"]["source_dataset_name"]),
        source_config={"operation": "publish_draft", "draft_id": draft_id},
        status="completed",
        started_at=now,
        ended_at=now,
        records_seen=len(draft["records"]),
        records_written=len(draft["records"]),
        error_message="",
        created_by_user_id=str(draft["updated_by_user_id"]),
    )
    return {"dataset_version": detail, "draft": _draft_response(draft), "job": job}


def create_dataset_version_from_candidates(
    storage_root: Path,
    dataset_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    latest = _latest_dataset_version(storage_root, dataset_id)
    candidate_ids = [int(candidate_id) for candidate_id in payload.get("candidate_ids", [])]
    candidate_status = str(payload.get("candidate_status") or "approved")
    candidates = _candidate_rows_for_dataset_iteration(
        storage_root=storage_root,
        dataset_id=dataset_id,
        status=candidate_status,
        candidate_ids=candidate_ids,
    )
    if not candidates:
        raise ValueError(
            f"no {candidate_status} dataset candidates are available for dataset_id {dataset_id}"
        )

    base_records = _records_for_full_snapshot(
        storage_root=storage_root,
        dataset_id=dataset_id,
        dataset_version_id=int(latest["dataset_version_id"]),
    )
    candidate_records = [
        {
            "source_row_id": f"candidate_{int(candidate['dataset_candidate_id'])}",
            "source_split": "train",
            "category": str(candidate.get("failure_type") or latest.get("category") or ""),
            "input_text": str(candidate.get("proposed_input_text") or ""),
            "instruction": str(candidate.get("proposed_input_text") or ""),
            "target_text": str(candidate.get("proposed_target_text") or ""),
            "response_text": str(candidate.get("proposed_target_text") or ""),
            "dataset_candidate_id": int(candidate["dataset_candidate_id"]),
            "eval_failure_id": int(candidate["eval_failure_id"]),
            "source_eval_run_id": int(candidate["source_eval_run_id"]),
            "source_eval_output_id": int(candidate["source_eval_output_id"]),
            "source_model_version_id": int(candidate["source_model_version_id"]),
            "source_priority": str(candidate.get("source_priority") or SourcePriority.GENERATED_REAL.value),
        }
        for candidate in candidates
    ]
    version_payload = {
        **latest,
        **payload,
        "dataset_version_id": int(payload.get("dataset_version_id") or int(latest["dataset_version_id"]) + 1),
        "records": [*base_records, *candidate_records],
        "parent_dataset_version_id": int(latest["dataset_version_id"]),
        "source_label": str(payload.get("source_label") or SourcePriority.GENERATED_REAL.value),
        "version_notes": str(
            payload.get("version_notes")
            or f"Created from {len(candidates)} approved dataset candidates."
        ),
    }
    detail = create_dataset_version(
        storage_root=storage_root,
        dataset_id=dataset_id,
        payload=version_payload,
    )
    created_at = str(payload.get("created_at") or utc_now_iso())
    included_candidate_ids = [int(candidate["dataset_candidate_id"]) for candidate in candidates]
    mark_candidates_included(
        storage_root=storage_root,
        candidate_ids=included_candidate_ids,
        dataset_id=dataset_id,
        dataset_version_id=int(detail["dataset_version_id"]),
        included_at=created_at,
    )
    manifest = {
        "dataset_id": dataset_id,
        "dataset_version_id": int(detail["dataset_version_id"]),
        "parent_dataset_version_id": int(latest["dataset_version_id"]),
        "candidate_status": candidate_status,
        "candidate_count": len(candidates),
        "included_candidate_ids": included_candidate_ids,
        "source_eval_failure_ids": sorted({int(candidate["eval_failure_id"]) for candidate in candidates}),
        "source_model_version_ids": sorted({int(candidate["source_model_version_id"]) for candidate in candidates}),
        "created_at": created_at,
        "created_by_user_id": str(payload.get("created_by_user_id") or DEFAULT_CREATED_BY_USER_ID),
    }
    _write_dataset_iteration_manifest(storage_root, manifest)
    return {
        "dataset_version": detail,
        "candidate_count": len(candidates),
        "included_candidate_ids": included_candidate_ids,
        "iteration_manifest": manifest,
    }


def get_dataset_ingestion_job(storage_root: Path, job_id: int) -> dict[str, Any] | None:
    path = _ingestion_job_path(storage_root, job_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_registered_version(
    storage_root: Path,
    payload: dict[str, Any],
    definition: DatasetDefinition,
    public_dataset_id: int,
    public_dataset_version_id: int,
    parent_dataset_version_id: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    created_at = str(payload.get("created_at") or utc_now_iso())
    source_label = _source_label(payload)
    storage_dataset_version_id = _storage_dataset_version_id(
        public_dataset_id=public_dataset_id,
        public_dataset_version_id=public_dataset_version_id,
    )
    raw_path = (
        storage_root
        / "raw"
        / "datasets"
        / definition.dataset_id
        / "versions"
        / storage_dataset_version_id
        / "records.jsonl"
    )
    normalized_records = [
        _normalize_registered_record(
            source_row=row,
            source_row_id=index,
            definition=definition,
            dataset_version_id=storage_dataset_version_id,
            source_label=source_label,
            created_at=created_at,
        )
        for index, row in enumerate(records, start=1)
    ]
    write_raw_jsonl(records, raw_path)
    result = write_dataset_outputs(
        storage_root=storage_root,
        definition=definition,
        source_records=records,
        normalized_records=normalized_records,
        raw_path=raw_path,
        dataset_version_id=storage_dataset_version_id,
        created_at=created_at,
    )
    _update_manifest(
        storage_root=storage_root,
        definition=definition,
        storage_dataset_version_id=storage_dataset_version_id,
        public_dataset_id=public_dataset_id,
        public_dataset_version_id=public_dataset_version_id,
        parent_dataset_version_id=parent_dataset_version_id,
        source_label=source_label,
        payload=payload,
    )
    detail = _repository(storage_root).get_dataset_version(
        str(public_dataset_id),
        str(public_dataset_version_id),
    )
    if detail is None:
        raise ValueError("dataset version was written but could not be read back")
    return {
        **detail,
        "raw_uri": result.raw_uri,
        "parquet_uri": result.parquet_uri,
    }


def _normalize_registered_record(
    source_row: dict[str, Any],
    source_row_id: int,
    definition: DatasetDefinition,
    dataset_version_id: str,
    source_label: str,
    created_at: str,
) -> dict[str, Any]:
    input_text = clean_text(
        source_row.get("input_text")
        or source_row.get("instruction")
        or source_row.get("prompt")
        or source_row.get("question")
    )
    instruction = clean_text(source_row.get("instruction") or input_text)
    context = clean_text(source_row.get("context"))
    question = clean_text(source_row.get("question"))
    chosen_text = clean_text(source_row.get("chosen_text") or source_row.get("chosen"))
    rejected_text = clean_text(source_row.get("rejected_text") or source_row.get("rejected"))
    target_text = clean_text(
        source_row.get("target_text")
        or source_row.get("response_text")
        or source_row.get("response")
        or source_row.get("answer")
        or source_row.get("completion")
        or chosen_text
    )
    response_text = clean_text(source_row.get("response_text") or source_row.get("response") or target_text)
    source_row_key = str(source_row.get("source_row_id") or source_row.get("id") or source_row_id)
    content_hash = content_hash_for_fields(
        input_text,
        instruction,
        context,
        question,
        chosen_text,
        rejected_text,
        target_text,
        response_text,
    )
    metadata = {
        key: value
        for key, value in source_row.items()
        if key
        not in {
            "input_text",
            "instruction",
            "prompt",
            "context",
            "question",
            "chosen_text",
            "chosen",
            "rejected_text",
            "rejected",
            "target_text",
            "response_text",
            "response",
            "answer",
            "completion",
        }
    }
    return {
        "record_id": build_record_id(dataset_version_id, "train", source_row_key, content_hash),
        "dataset_id": definition.dataset_id,
        "dataset_version_id": dataset_version_id,
        "source_dataset_name": definition.source_dataset_name,
        "source_split": clean_text(source_row.get("source_split") or "train"),
        "source_row_id": source_row_key,
        "category": clean_text(source_row.get("category") or definition.category),
        "task_type": definition.task_type,
        "input_text": input_text,
        "instruction": instruction,
        "context": context,
        "question": question,
        "chosen_text": chosen_text,
        "rejected_text": rejected_text,
        "target_text": target_text,
        "response_text": response_text,
        "prompt_messages_json": json.dumps([{"role": "user", "content": instruction or input_text}], ensure_ascii=True),
        "metadata_json": json.dumps(metadata, sort_keys=True, ensure_ascii=True),
        "content_hash": content_hash,
        "source_label": source_label,
        "created_at": created_at,
    }


def _definition_from_payload(
    payload: dict[str, Any],
    public_dataset_id: int,
    existing_storage_dataset_id: str | None,
) -> DatasetDefinition:
    name = str(payload.get("name") or payload.get("display_name") or "").strip()
    if not name:
        raise ValueError("name is required")
    task_type = str(payload.get("task_type") or payload.get("default_task_type") or "").strip()
    if not task_type:
        raise ValueError("task_type is required")
    storage_dataset_id = existing_storage_dataset_id or f"ds_dataset_{public_dataset_id}"
    source_dataset_name = str(payload.get("source_dataset_name") or name).strip()
    return DatasetDefinition(
        dataset_id=storage_dataset_id,
        slug=_slug_for_storage(storage_dataset_id),
        display_name=name,
        source_dataset_name=source_dataset_name,
        category=str(payload.get("category") or task_type.replace("_", " ")).strip(),
        task_type=task_type,
        description=str(payload.get("description") or "").strip(),
        transform_name=str(payload.get("transform_name") or "normalize_registered_dataset_records").strip(),
    )


def _update_manifest(
    storage_root: Path,
    definition: DatasetDefinition,
    storage_dataset_version_id: str,
    public_dataset_id: int,
    public_dataset_version_id: int,
    parent_dataset_version_id: str,
    source_label: str,
    payload: dict[str, Any],
) -> None:
    path = (
        storage_root
        / "object_store"
        / "datasets"
        / definition.dataset_id
        / "versions"
        / storage_dataset_version_id
        / "manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    manifest.update(
        {
            "public_dataset_id": public_dataset_id,
            "public_dataset_version_id": public_dataset_version_id,
            "display_name": str(payload.get("name") or definition.display_name),
            "description": str(payload.get("description") or definition.description),
            "category": str(payload.get("category") or definition.category),
            "task_type": definition.task_type,
            "data_purpose": str(payload.get("data_purpose") or _default_data_purpose(definition.task_type)),
            "data_format": "Parquet",
            "query_engine": "DuckDB",
            "source_url": str(payload.get("source_url") or ""),
            "source_priority": source_label,
            "parent_dataset_version_id": parent_dataset_version_id,
            "created_by_user_id": str(payload.get("created_by_user_id") or DEFAULT_CREATED_BY_USER_ID),
            "version_notes": str(payload.get("version_notes") or ""),
            "data_structure": str(payload.get("data_structure") or "structured"),
        }
    )
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _records_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list of objects")
    if not all(isinstance(record, dict) for record in records):
        raise ValueError("records must be a non-empty list of objects")
    return records


def _latest_dataset_version(storage_root: Path, dataset_id: int) -> dict[str, Any]:
    repository = _repository(storage_root)
    existing_versions = repository.list_dataset_versions(str(dataset_id))
    if not existing_versions:
        raise ValueError(f"dataset_id {dataset_id} does not exist")
    return max(existing_versions, key=lambda version: int(version["dataset_version_id"]))


def _draft_metadata_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(payload.get("name") or payload.get("display_name") or ""),
        "display_name": str(payload.get("name") or payload.get("display_name") or ""),
        "description": str(payload.get("description") or ""),
        "source_url": str(payload.get("source_url") or ""),
        "source_dataset_name": str(payload.get("source_dataset_name") or payload.get("name") or payload.get("display_name") or ""),
        "source_label": str(payload.get("source_label") or SourcePriority.SYNTHETIC_REALISTIC.value),
        "task_type": str(payload.get("task_type") or payload.get("default_task_type") or ""),
        "data_purpose": str(payload.get("data_purpose") or ""),
        "category": str(payload.get("category") or ""),
        "transform_name": str(payload.get("transform_name") or "normalize_registered_dataset_records"),
    }


def _draft_root(storage_root: Path, dataset_id: int) -> Path:
    return storage_root / "object_store" / "datasets" / _storage_dataset_id_for_display_id(dataset_id) / "drafts"


def _draft_path(storage_root: Path, dataset_id: int, draft_id: str) -> Path:
    return _draft_root(storage_root, dataset_id) / draft_id / "draft.json"


def _next_draft_id(storage_root: Path, dataset_id: int) -> str:
    ids = []
    for path in _draft_root(storage_root, dataset_id).glob("draft_*"):
        match = re.fullmatch(r"draft_(\d+)", path.name)
        if match:
            ids.append(int(match.group(1)))
    return f"draft_{max(ids, default=0) + 1}"


def _read_draft(storage_root: Path, dataset_id: int, draft_id: str) -> dict[str, Any]:
    path = _draft_path(storage_root, dataset_id, draft_id)
    if not path.exists():
        raise ValueError(f"draft_id {draft_id} not found for dataset_id {dataset_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_mutable_draft(storage_root: Path, dataset_id: int, draft_id: str) -> dict[str, Any]:
    draft = _read_draft(storage_root, dataset_id, draft_id)
    if draft["status"] == PUBLISHED_STATUS:
        raise ValueError(f"draft_id {draft_id} is already published")
    return draft


def _write_draft(storage_root: Path, dataset_id: int, draft_id: str, draft: dict[str, Any]) -> None:
    path = _draft_path(storage_root, dataset_id, draft_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(draft, indent=2, sort_keys=True), encoding="utf-8")


def _draft_response(draft: dict[str, Any], job: dict[str, Any] | None = None) -> dict[str, Any]:
    response = {
        key: value
        for key, value in draft.items()
        if key not in {"records"}
    }
    if job is not None:
        response["job"] = job
    return response


def _records_for_full_snapshot(
    storage_root: Path,
    dataset_id: int,
    dataset_version_id: int,
) -> list[dict[str, Any]]:
    rows = _repository(storage_root).list_records(
        dataset_id=str(dataset_id),
        dataset_version_id=str(dataset_version_id),
        limit=1_000_000,
    )
    return [
        {
            "source_row_id": str(row.get("source_row_id") or index),
            "source_split": str(row.get("source_split") or "train"),
            "category": str(row.get("category") or ""),
            "input_text": str(row.get("input_text") or ""),
            "instruction": str(row.get("instruction") or row.get("input_text") or ""),
            "context": str(row.get("context") or ""),
            "question": str(row.get("question") or ""),
            "chosen_text": str(row.get("chosen_text") or ""),
            "rejected_text": str(row.get("rejected_text") or ""),
            "target_text": str(row.get("target_text") or row.get("response_text") or ""),
            "response_text": str(row.get("response_text") or row.get("target_text") or ""),
        }
        for index, row in enumerate(rows, start=1)
    ]


def _candidate_rows_for_dataset_iteration(
    storage_root: Path,
    dataset_id: int,
    status: str,
    candidate_ids: list[int],
) -> list[dict[str, Any]]:
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    register_dataset_candidate_duckdb_view(storage_root=storage_root, duckdb_path=duckdb_path)
    if not duckdb_path.exists() or not _duckdb_table_exists(duckdb_path, "dataset_candidates"):
        return []
    filters = ["target_dataset_id = ?", "status = ?"]
    params: list[Any] = [int(dataset_id), status]
    if _duckdb_column_exists(duckdb_path, "dataset_candidates", "included_dataset_version_id"):
        filters.append("COALESCE(included_dataset_version_id, 0) = 0")
    if candidate_ids:
        placeholders = ", ".join("?" for _ in candidate_ids)
        filters.append(f"dataset_candidate_id IN ({placeholders})")
        params.extend(candidate_ids)
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        result = connection.execute(
            f"""
            SELECT *
            FROM dataset_candidates
            WHERE {" AND ".join(filters)}
            ORDER BY created_at, dataset_candidate_id
            """,
            params,
        )
        columns = [column[0] for column in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    finally:
        connection.close()


def _duckdb_table_exists(duckdb_path: Path, table_name: str) -> bool:
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            connection.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
        except duckdb.Error:
            return False
        return True
    finally:
        connection.close()


def _duckdb_column_exists(duckdb_path: Path, table_name: str, column_name: str) -> bool:
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            result = connection.execute(f"DESCRIBE {table_name}")
        except duckdb.Error:
            return False
        rows = result.fetchall()
        columns = [column[0] for column in result.description]
        return any(dict(zip(columns, row, strict=True)).get("column_name") == column_name for row in rows)
    finally:
        connection.close()


def _write_dataset_iteration_manifest(storage_root: Path, manifest: dict[str, Any]) -> None:
    path = (
        storage_root
        / "object_store"
        / "dataset_iterations"
        / f"dataset_id={manifest['dataset_id']}"
        / f"dataset_version_id={manifest['dataset_version_id']}"
        / "iteration_manifest.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _quality_issues_from_metrics(
    quality_metrics: list[dict[str, Any]],
    schema_profile: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    metrics = {row["metric_name"]: row["metric_value"] for row in quality_metrics}
    issues: list[dict[str, Any]] = []
    if float(metrics.get("records.empty_required_field_count", 0)) > 0:
        issues.append(
            {
                "severity": "error",
                "issue_type": "required_field_missing",
                "message": "One or more records are missing required input or target text.",
            }
        )
    if float(metrics.get("records.duplicate_exact_count", 0)) > 0:
        issues.append(
            {
                "severity": "warning",
                "issue_type": "duplicate_records",
                "message": "Exact duplicate normalized records were detected.",
            }
        )
    if float(metrics.get("pii.fake_test_match_count", 0)) > 0:
        issues.append(
            {
                "severity": "warning",
                "issue_type": "safe_pii_pattern_match",
                "message": "Safe fake/test PII patterns were detected by the MVP scanner.",
            }
        )
    if not schema_profile:
        issues.append(
            {
                "severity": "error",
                "issue_type": "schema_profile_missing",
                "message": "Schema profile could not be generated.",
            }
        )
    return issues


def _write_quality_issues(
    storage_root: Path,
    dataset_id: int,
    draft_id: str,
    issues: list[dict[str, Any]],
) -> None:
    path = _draft_root(storage_root, dataset_id) / draft_id / "quality_issues.json"
    path.write_text(json.dumps({"items": issues}, indent=2, sort_keys=True), encoding="utf-8")


def _ingestion_jobs_root(storage_root: Path) -> Path:
    return storage_root / "object_store" / "dataset_ingestion_jobs"


def _next_ingestion_job_id(storage_root: Path) -> int:
    ids = []
    for path in _ingestion_jobs_root(storage_root).glob("job_*.json"):
        match = re.fullmatch(r"job_(\d+)\.json", path.name)
        if match:
            ids.append(int(match.group(1)))
    return max(ids, default=0) + 1


def _ingestion_job_path(storage_root: Path, job_id: int) -> Path:
    return _ingestion_jobs_root(storage_root) / f"job_{job_id}.json"


def _write_ingestion_job(
    storage_root: Path,
    dataset_id: int,
    source_dataset_name: str,
    source_config: dict[str, Any],
    status: str,
    started_at: str,
    ended_at: str,
    records_seen: int,
    records_written: int,
    error_message: str,
    created_by_user_id: str,
) -> dict[str, Any]:
    job_id = _next_ingestion_job_id(storage_root)
    job = {
        "dataset_ingestion_job_id": job_id,
        "dataset_id": dataset_id,
        "source_dataset_name": source_dataset_name,
        "source_config_json": json.dumps(source_config, sort_keys=True, ensure_ascii=True),
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "records_seen": records_seen,
        "records_written": records_written,
        "error_message": error_message,
        "created_by_user_id": created_by_user_id,
    }
    path = _ingestion_job_path(storage_root, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job, indent=2, sort_keys=True), encoding="utf-8")
    return job


def _source_label(payload: dict[str, Any]) -> str:
    raw_source_label = str(payload.get("source_label") or SourcePriority.SYNTHETIC_REALISTIC.value)
    allowed = {item.value for item in SourcePriority}
    if raw_source_label not in allowed:
        raise ValueError(f"source_label must be one of: {', '.join(sorted(allowed))}")
    return raw_source_label


def _next_dataset_id(storage_root: Path) -> int:
    existing_ids = set(_existing_dataset_ids(storage_root)) | {1, 2, 3, 4, 5, 6, 7, 8}
    return (max(existing_ids) + 1) if existing_ids else 1


def _existing_dataset_ids(storage_root: Path) -> list[int]:
    ids: set[int] = set()
    for path in (storage_root / "parquet" / "dataset_records").glob("dataset_id=*"):
        ids.add(_dataset_display_id_for_storage_id(path.name.removeprefix("dataset_id=")))
    duckdb_path = storage_root / "duckdb" / "research_command_center.duckdb"
    if duckdb_path.exists():
        connection = duckdb.connect(str(duckdb_path), read_only=True)
        try:
            rows = connection.execute("SELECT DISTINCT dataset_id FROM dataset_records").fetchall()
            ids.update(_dataset_display_id_for_storage_id(str(row[0])) for row in rows)
        except duckdb.Error:
            pass
        finally:
            connection.close()
    return [dataset_id for dataset_id in ids if dataset_id > 0]


def _dataset_exists(storage_root: Path, dataset_id: int) -> bool:
    return dataset_id in _existing_dataset_ids(storage_root)


def _repository(storage_root: Path) -> DatasetRepository:
    return DatasetRepository(
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
        storage_root=storage_root,
    )


def _storage_dataset_version_id(public_dataset_id: int, public_dataset_version_id: int) -> str:
    return f"dsv_dataset_{public_dataset_id}_v{public_dataset_version_id}"


def _slug_for_storage(storage_dataset_id: str) -> str:
    return re.sub(r"^ds_", "", storage_dataset_id)


def _default_data_purpose(task_type: str) -> str:
    return task_type.replace("_", " ").title()
