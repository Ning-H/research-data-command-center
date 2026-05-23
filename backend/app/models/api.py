from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.models.lifecycle import register_model_duckdb_views, register_model_from_checkpoint
from app.models.repository import ModelRepository

router = APIRouter(prefix="/models", tags=["models"])


def get_model_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


def get_model_repository() -> ModelRepository:
    storage_root = get_model_storage_root()
    duckdb_path = Path(settings.duckdb_path)
    if not _duckdb_has_table(duckdb_path, "model_versions"):
        register_model_duckdb_views(storage_root=storage_root, duckdb_path=duckdb_path)
    return ModelRepository(duckdb_path=duckdb_path, storage_root=storage_root)


@router.get("")
def list_models(
    repository: Annotated[ModelRepository, Depends(get_model_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_model_versions(limit=limit, offset=offset),
        "limit": limit,
        "offset": offset,
    }


@router.post("/register-from-checkpoint")
def register_from_checkpoint(
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_model_storage_root)],
) -> dict[str, Any]:
    try:
        result = register_model_from_checkpoint(storage_root=storage_root, payload=payload)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "model_id": result.model_id,
        "model_version_id": result.model_version_id,
        "checkpoint_id": result.checkpoint_id,
        "run_id": result.run_id,
        "dataset_id": result.dataset_id,
        "dataset_version_id": result.dataset_version_id,
        "status": result.status,
        "artifact_uri": result.artifact_uri,
    }


@router.get("/{model_version_id}")
def get_model(
    model_version_id: int,
    repository: Annotated[ModelRepository, Depends(get_model_repository)],
) -> dict[str, Any]:
    model = repository.get_model_version(model_version_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Model version not found: {model_version_id}")
    return model


@router.get("/{model_version_id}/lineage")
def get_model_lineage(
    model_version_id: int,
    repository: Annotated[ModelRepository, Depends(get_model_repository)],
) -> dict[str, Any]:
    return {"items": repository.get_lineage(model_version_id)}


def _duckdb_has_table(duckdb_path: Path, table_name: str) -> bool:
    if not duckdb_path.exists():
        return False
    connection = duckdb.connect(str(duckdb_path), read_only=True)
    try:
        try:
            connection.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
        except duckdb.Error:
            return False
        return True
    finally:
        connection.close()
