from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.config import settings
from app.datasets.lifecycle import (
    append_dataset_draft_records,
    create_dataset_draft,
    create_dataset_version,
    create_dataset_version_from_candidates,
    get_dataset_ingestion_job,
    overwrite_dataset_draft_records,
    publish_dataset_draft,
    register_dataset,
    register_raw_dataset,
    validate_dataset_draft,
)
from app.datasets.repository import DatasetRepository
from app.research_programs.lifecycle import attach_research_program_links

router = APIRouter(prefix="/datasets", tags=["datasets"])
jobs_router = APIRouter(prefix="/dataset-ingestion-jobs", tags=["datasets"])


def get_dataset_repository() -> DatasetRepository:
    return DatasetRepository(
        duckdb_path=Path(settings.duckdb_path),
        storage_root=Path(settings.raw_storage_root).parent,
    )


def get_dataset_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


@router.get("")
def list_datasets(
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
    q: str | None = None,
    task_type: str | None = None,
    source_label: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    items = repository.list_datasets(
        q=q,
        task_type=task_type,
        source_label=source_label,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "limit": limit, "offset": offset}


@router.get("/{dataset_id}")
def get_dataset(
    dataset_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> dict[str, Any]:
    dataset = repository.get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    return dataset


@router.get("/{dataset_id}/versions")
def list_dataset_versions(
    dataset_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> dict[str, Any]:
    items = repository.list_dataset_versions(dataset_id)
    if not items:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    return {"items": items}


@router.get("/{dataset_id}/versions/{dataset_version_id}")
def get_dataset_version(
    dataset_id: str,
    dataset_version_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> dict[str, Any]:
    dataset = repository.get_dataset_version(dataset_id, dataset_version_id)
    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset version not found: dataset_id={dataset_id}, dataset_version_id={dataset_version_id}",
        )
    return dataset


@router.post("/register")
def register_dataset_endpoint(
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    try:
        return register_dataset(storage_root=storage_root, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/register-raw")
async def register_raw_dataset_endpoint(
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
    file: Annotated[UploadFile, File()],
    name: Annotated[str, Form()],
    source_label: Annotated[str, Form()] = "SYNTHETIC_REALISTIC",
    description: Annotated[str, Form()] = "",
    data_purpose: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    task_type: Annotated[str, Form()] = "",
    data_structure: Annotated[str, Form()] = "unstructured",
) -> dict[str, Any]:
    data = await file.read()
    try:
        return register_raw_dataset(
            storage_root=storage_root,
            data=data,
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            payload={
                "name": name,
                "source_label": source_label,
                "description": description,
                "data_purpose": data_purpose,
                "category": category,
                "task_type": task_type,
                "data_structure": data_structure,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/versions")
def create_dataset_version_endpoint(
    dataset_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    try:
        return create_dataset_version(storage_root=storage_root, dataset_id=dataset_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/versions/from-candidates")
def create_dataset_version_from_candidates_endpoint(
    dataset_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    try:
        return create_dataset_version_from_candidates(
            storage_root=storage_root,
            dataset_id=dataset_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/versions/draft")
def create_dataset_draft_endpoint(
    dataset_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    try:
        return create_dataset_draft(storage_root=storage_root, dataset_id=dataset_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/versions/{draft_id}/append")
def append_dataset_draft_endpoint(
    dataset_id: int,
    draft_id: str,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    try:
        return append_dataset_draft_records(
            storage_root=storage_root,
            dataset_id=dataset_id,
            draft_id=draft_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/versions/{draft_id}/overwrite")
def overwrite_dataset_draft_endpoint(
    dataset_id: int,
    draft_id: str,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    try:
        return overwrite_dataset_draft_records(
            storage_root=storage_root,
            dataset_id=dataset_id,
            draft_id=draft_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/versions/{draft_id}/validate")
def validate_dataset_draft_endpoint(
    dataset_id: int,
    draft_id: str,
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return validate_dataset_draft(
            storage_root=storage_root,
            dataset_id=dataset_id,
            draft_id=draft_id,
            payload=payload or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{dataset_id}/versions/{draft_id}/publish")
def publish_dataset_draft_endpoint(
    dataset_id: int,
    draft_id: str,
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return publish_dataset_draft(
            storage_root=storage_root,
            dataset_id=dataset_id,
            draft_id=draft_id,
            payload=payload or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{dataset_id}/versions/{dataset_version_id}/records")
def list_dataset_records(
    dataset_id: str,
    dataset_version_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: str | None = None,
) -> dict[str, Any]:
    return {
        "items": repository.list_records(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            limit=limit,
            offset=offset,
            q=q,
        )
    }


@jobs_router.get("/{job_id}")
def get_dataset_ingestion_job_endpoint(
    job_id: int,
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    job = get_dataset_ingestion_job(storage_root=storage_root, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Dataset ingestion job not found: {job_id}")
    return job


@router.get("/{dataset_id}/versions/{dataset_version_id}/quality")
def get_dataset_quality(
    dataset_id: str,
    dataset_version_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> dict[str, Any]:
    return {
        "items": repository.get_quality_metrics(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
        )
    }


@router.get("/{dataset_id}/versions/{dataset_version_id}/schema")
def get_dataset_schema(
    dataset_id: str,
    dataset_version_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> dict[str, Any]:
    return {
        "items": repository.get_schema_profile(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
        )
    }


@router.get("/{dataset_id}/versions/{dataset_version_id}/lineage")
def get_dataset_lineage(
    dataset_id: str,
    dataset_version_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> dict[str, Any]:
    return {
        "items": repository.get_lineage(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
        )
    }


@router.get("/{dataset_id}/versions/{dataset_version_id}/experiment-handoff")
def get_dataset_experiment_handoff(
    dataset_id: str,
    dataset_version_id: str,
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
) -> dict[str, Any]:
    handoff = repository.get_experiment_handoff(dataset_id, dataset_version_id)
    if handoff is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset version not found: dataset_id={dataset_id}, dataset_version_id={dataset_version_id}",
        )
    return handoff


@router.post("/{dataset_id}/versions/{dataset_version_id}/access")
def record_dataset_access(
    dataset_id: int,
    dataset_version_id: int,
    payload: dict[str, Any],
    repository: Annotated[DatasetRepository, Depends(get_dataset_repository)],
    storage_root: Annotated[Path, Depends(get_dataset_storage_root)],
) -> dict[str, Any]:
    dataset = repository.get_dataset(str(dataset_id))
    if dataset is None:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    program_id = int(payload["program_id"])
    try:
        program = attach_research_program_links(
            storage_root=storage_root,
            program_id=program_id,
            dataset_ids=[dataset_id],
            dataset_versions=[
                {"dataset_id": dataset_id, "dataset_version_id": int(dataset_version_id)}
            ],
            updated_by_user_id=payload.get("user_id") or payload.get("updated_by_user_id"),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "program_id": program_id,
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "access_purpose": payload.get("access_purpose", "not_provided"),
        "linked_datasets": program["linked_datasets"],
        "note": "Dataset usage recorded against the research program from an API access request.",
    }
