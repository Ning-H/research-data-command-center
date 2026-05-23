from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.runs.ingestion import ingest_run_payload
from app.runs.lifecycle import (
    append_run_checkpoints,
    append_run_events,
    complete_run,
    register_run,
)
from app.runs.repository import RunRepository

router = APIRouter(prefix="/runs", tags=["runs"])
checkpoints_router = APIRouter(prefix="/checkpoints", tags=["checkpoints"])


def get_run_repository() -> RunRepository:
    return RunRepository(duckdb_path=Path(settings.duckdb_path), storage_root=Path("."))


def get_run_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


@router.get("")
def list_runs(
    repository: Annotated[RunRepository, Depends(get_run_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {"items": repository.list_runs(limit=limit, offset=offset), "limit": limit, "offset": offset}


@router.post("/ingest")
def ingest_run(
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_run_storage_root)],
) -> dict[str, Any]:
    result = ingest_run_payload(storage_root=storage_root, payload=payload)
    return {
        "run_id": result.run_id,
        "run_config_id": result.run_config_id,
        "dataset_version_id": result.dataset_version_id,
        "checkpoint_count": result.checkpoint_count,
        "raw_events_uri": result.raw_events_uri,
    }


@router.post("/register")
def register_training_run(
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_run_storage_root)],
) -> dict[str, Any]:
    try:
        result = register_run(storage_root=storage_root, payload=payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "run_id": result.run_id,
        "run_config_id": result.run_config_id,
        "dataset_id": result.dataset_id,
        "dataset_version_id": result.dataset_version_id,
        "status": result.status,
        "raw_events_uri": result.raw_events_uri,
    }


@router.get("/{run_id}")
def get_run(
    run_id: int,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> dict[str, Any]:
    run = repository.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run


@router.get("/{run_id}/metrics")
def list_run_metrics(
    run_id: int,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> dict[str, Any]:
    return {"items": repository.list_metrics(run_id)}


@router.get("/{run_id}/compute")
def list_run_compute(
    run_id: int,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> dict[str, Any]:
    return {"items": repository.list_compute_metrics(run_id)}


@router.post("/{run_id}/events")
def append_events(
    run_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_run_storage_root)],
) -> dict[str, Any]:
    try:
        result = append_run_events(
            storage_root=storage_root,
            run_id=run_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "run_id": result.run_id,
        "appended_count": result.appended_count,
        "raw_events_uri": result.raw_events_uri,
    }


@router.get("/{run_id}/checkpoints")
def list_run_checkpoints(
    run_id: int,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> dict[str, Any]:
    return {"items": repository.list_checkpoints(run_id)}


@router.post("/{run_id}/checkpoints")
def append_checkpoints(
    run_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_run_storage_root)],
) -> dict[str, Any]:
    try:
        result = append_run_checkpoints(
            storage_root=storage_root,
            run_id=run_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "run_id": result.run_id,
        "appended_count": result.appended_count,
        "raw_events_uri": result.raw_events_uri,
    }


@router.get("/{run_id}/lineage")
def get_run_lineage(
    run_id: int,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> dict[str, Any]:
    return {"items": repository.get_lineage(run_id)}


@router.post("/{run_id}/complete")
def complete_training_run(
    run_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_run_storage_root)],
) -> dict[str, Any]:
    try:
        result = complete_run(
            storage_root=storage_root,
            run_id=run_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"run_id": result.run_id, "status": result.status, "ended_at": result.ended_at}


@checkpoints_router.get("")
def search_checkpoints(
    repository: Annotated[RunRepository, Depends(get_run_repository)],
    dataset_id: int | None = None,
    dataset_version_id: int | None = None,
    framework: str | None = None,
    trainer: str | None = None,
    run_status: str | None = "completed",
    ranking_metric: str = "train.accuracy",
    direction: str = "desc",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    if direction not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="direction must be asc or desc")
    return {
        "items": repository.search_checkpoints(
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            framework=framework,
            trainer=trainer,
            run_status=run_status,
            ranking_metric=ranking_metric,
            direction=direction,
            limit=limit,
            offset=offset,
        ),
        "filters": {
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "framework": framework,
            "trainer": trainer,
            "run_status": run_status,
            "ranking_metric": ranking_metric,
            "direction": direction,
        },
        "limit": limit,
        "offset": offset,
    }
