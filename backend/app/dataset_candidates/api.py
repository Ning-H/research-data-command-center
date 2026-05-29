from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.dataset_candidates.lifecycle import create_dataset_candidate, update_dataset_candidate
from app.dataset_candidates.repository import DatasetCandidateRepository

router = APIRouter(tags=["dataset-candidates"])


def get_dataset_candidate_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


def get_dataset_candidate_repository() -> DatasetCandidateRepository:
    storage_root = get_dataset_candidate_storage_root()
    return DatasetCandidateRepository(
        duckdb_path=Path(settings.duckdb_path),
        storage_root=storage_root,
    )


@router.post("/dataset-candidates")
def create_candidate(
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_candidate_storage_root)],
) -> dict[str, Any]:
    try:
        result = create_dataset_candidate(storage_root=storage_root, payload=payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "dataset_candidate_id": result.dataset_candidate_id,
        "eval_failure_id": result.eval_failure_id,
        "source_eval_run_id": result.source_eval_run_id,
        "source_model_version_id": result.source_model_version_id,
        "status": result.status,
    }


@router.post("/eval-failures/{eval_failure_id}/dataset-candidate")
def create_candidate_from_failure(
    eval_failure_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_candidate_storage_root)],
) -> dict[str, Any]:
    return create_candidate(
        payload={**payload, "eval_failure_id": eval_failure_id},
        storage_root=storage_root,
    )


@router.patch("/dataset-candidates/{dataset_candidate_id}")
def review_candidate(
    dataset_candidate_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_dataset_candidate_storage_root)],
) -> dict[str, Any]:
    try:
        return update_dataset_candidate(
            storage_root=storage_root,
            dataset_candidate_id=dataset_candidate_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dataset-candidates")
def list_candidates(
    repository: Annotated[DatasetCandidateRepository, Depends(get_dataset_candidate_repository)],
    program_id: int | None = None,
    experiment_id: int | None = None,
    target_dataset_id: int | None = None,
    source_model_version_id: int | None = None,
    failure_type: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_candidates(
            program_id=program_id,
            experiment_id=experiment_id,
            target_dataset_id=target_dataset_id,
            source_model_version_id=source_model_version_id,
            failure_type=failure_type,
            status=status,
            limit=limit,
            offset=offset,
        ),
        "filters": {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "target_dataset_id": target_dataset_id,
            "source_model_version_id": source_model_version_id,
            "failure_type": failure_type,
            "status": status,
        },
        "limit": limit,
        "offset": offset,
    }


@router.get("/dataset-iterations")
def list_dataset_iterations(
    repository: Annotated[DatasetCandidateRepository, Depends(get_dataset_candidate_repository)],
    program_id: int | None = None,
    experiment_id: int | None = None,
    target_dataset_id: int | None = None,
    failure_type: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    return {
        "items": repository.list_dataset_iterations(
            program_id=program_id,
            experiment_id=experiment_id,
            target_dataset_id=target_dataset_id,
            failure_type=failure_type,
            status=status,
        ),
        "filters": {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "target_dataset_id": target_dataset_id,
            "failure_type": failure_type,
            "status": status,
        },
    }


@router.get("/dataset-candidates/{dataset_candidate_id}")
def get_candidate(
    dataset_candidate_id: int,
    repository: Annotated[DatasetCandidateRepository, Depends(get_dataset_candidate_repository)],
) -> dict[str, Any]:
    candidate = repository.get_candidate(dataset_candidate_id)
    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset candidate not found: {dataset_candidate_id}",
        )
    return candidate
