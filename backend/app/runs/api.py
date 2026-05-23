from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.runs.ingestion import ingest_run_payload
from app.runs.repository import RunRepository

router = APIRouter(prefix="/runs", tags=["runs"])


def get_run_repository() -> RunRepository:
    return RunRepository(duckdb_path=Path(settings.duckdb_path), storage_root=Path("."))


@router.get("")
def list_runs(
    repository: Annotated[RunRepository, Depends(get_run_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {"items": repository.list_runs(limit=limit, offset=offset), "limit": limit, "offset": offset}


@router.post("/ingest")
def ingest_run(payload: dict[str, Any]) -> dict[str, Any]:
    result = ingest_run_payload(storage_root=Path(settings.raw_storage_root).parent, payload=payload)
    return {
        "run_id": result.run_id,
        "run_config_id": result.run_config_id,
        "dataset_version_id": result.dataset_version_id,
        "checkpoint_count": result.checkpoint_count,
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


@router.get("/{run_id}/checkpoints")
def list_run_checkpoints(
    run_id: int,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> dict[str, Any]:
    return {"items": repository.list_checkpoints(run_id)}


@router.get("/{run_id}/lineage")
def get_run_lineage(
    run_id: int,
    repository: Annotated[RunRepository, Depends(get_run_repository)],
) -> dict[str, Any]:
    return {"items": repository.get_lineage(run_id)}
