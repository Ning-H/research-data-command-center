from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.experiments.lifecycle import register_experiment, update_experiment
from app.experiments.repository import ExperimentRepository

router = APIRouter(prefix="/experiments", tags=["experiments"])


def get_experiment_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


def get_experiment_repository() -> ExperimentRepository:
    storage_root = get_experiment_storage_root()
    return ExperimentRepository(
        duckdb_path=Path(settings.duckdb_path),
        storage_root=storage_root,
    )


@router.get("")
def list_experiments(
    repository: Annotated[ExperimentRepository, Depends(get_experiment_repository)],
    program_id: int | None = None,
    status: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_experiments(
            program_id=program_id,
            status=status,
            tag=tag,
            q=q,
            limit=limit,
            offset=offset,
        ),
        "limit": limit,
        "offset": offset,
        "filters": {"program_id": program_id, "status": status, "tag": tag, "q": q},
    }


@router.post("")
def create_experiment(
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_experiment_storage_root)],
) -> dict[str, Any]:
    try:
        result = register_experiment(storage_root=storage_root, payload=payload)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "experiment_id": result.experiment_id,
        "program_id": result.program_id,
        "experiment_name": result.experiment_name,
        "status": result.status,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


@router.get("/{experiment_id}")
def get_experiment(
    experiment_id: int,
    repository: Annotated[ExperimentRepository, Depends(get_experiment_repository)],
) -> dict[str, Any]:
    experiment = repository.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
    return experiment


@router.patch("/{experiment_id}")
def patch_experiment(
    experiment_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_experiment_storage_root)],
    repository: Annotated[ExperimentRepository, Depends(get_experiment_repository)],
) -> dict[str, Any]:
    try:
        update_experiment(storage_root=storage_root, experiment_id=experiment_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    experiment = repository.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
    return experiment
