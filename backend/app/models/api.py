from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.evaluations.repository import EvaluationRepository
from app.models.lifecycle import register_model_from_checkpoint
from app.models.repository import ModelRepository

router = APIRouter(prefix="/models", tags=["models"])


def get_model_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


def get_model_repository() -> ModelRepository:
    storage_root = get_model_storage_root()
    duckdb_path = Path(settings.duckdb_path)
    return ModelRepository(duckdb_path=duckdb_path, storage_root=storage_root)


def get_model_evaluation_repository(
    storage_root: Annotated[Path, Depends(get_model_storage_root)],
) -> EvaluationRepository:
    return EvaluationRepository(
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
        storage_root=storage_root,
    )


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


@router.post("/compare")
def compare_models(
    payload: dict[str, Any],
    repository: Annotated[EvaluationRepository, Depends(get_model_evaluation_repository)],
) -> dict[str, Any]:
    try:
        return repository.compare_model_versions(
            model_version_ids=[int(value) for value in payload.get("model_version_ids", [])],
            baseline_model_version_id=payload.get("baseline_model_version_id"),
            experiment_id=payload.get("experiment_id"),
            eval_suite_id=payload.get("eval_suite_id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{model_version_id}/evals")
def get_model_evals(
    model_version_id: int,
    repository: Annotated[EvaluationRepository, Depends(get_model_evaluation_repository)],
) -> dict[str, Any]:
    return {
        "model_version_id": model_version_id,
        "items": repository.list_eval_runs(model_version_id=model_version_id),
        "summary": repository.evaluation_summary(model_version_id=model_version_id),
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
