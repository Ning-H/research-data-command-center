from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.datasets.repository import DatasetRepository
from app.experiments.lifecycle import (
    append_experiment_note,
    attach_experiment_links,
    register_experiment,
    update_experiment,
)
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


@router.get("/{experiment_id}/next-run-plan")
def get_next_run_plan(
    experiment_id: int,
    repository: Annotated[ExperimentRepository, Depends(get_experiment_repository)],
) -> dict[str, Any]:
    plan = repository.get_next_run_plan(experiment_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
    return plan


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


@router.post("/{experiment_id}/notes")
def append_note(
    experiment_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_experiment_storage_root)],
    repository: Annotated[ExperimentRepository, Depends(get_experiment_repository)],
) -> dict[str, Any]:
    try:
        result = append_experiment_note(
            storage_root=storage_root,
            experiment_id=experiment_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    experiment = repository.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")
    return {
        "experiment_id": result.experiment_id,
        "note_id": result.note_id,
        "notes": result.notes,
        "updated_at": result.updated_at,
        "experiment": experiment,
    }


@router.post("/{experiment_id}/dataset-handoffs")
def accept_dataset_handoff(
    experiment_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_experiment_storage_root)],
    repository: Annotated[ExperimentRepository, Depends(get_experiment_repository)],
) -> dict[str, Any]:
    try:
        dataset_id = int(payload["dataset_id"])
        dataset_version_id = int(payload["dataset_version_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="dataset_id and dataset_version_id are required",
        ) from exc

    dataset_repository = DatasetRepository(
        duckdb_path=repository.duckdb_path,
        storage_root=storage_root,
    )
    handoff = dataset_repository.get_experiment_handoff(
        dataset_id=str(dataset_id),
        dataset_version_id=str(dataset_version_id),
    )
    if handoff is None:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset version not found: dataset_id={dataset_id}, dataset_version_id={dataset_version_id}",
        )

    recommended_experiment_id = int(
        handoff["recommended_next_experiment"].get("experiment_id") or 0
    )
    if recommended_experiment_id and recommended_experiment_id != experiment_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "dataset handoff belongs to "
                f"experiment_id={recommended_experiment_id}, not experiment_id={experiment_id}"
            ),
        )

    actor = str(payload.get("updated_by_user_id") or payload.get("author_name") or "user_demo_owner")
    dataset_ref = {"dataset_id": dataset_id, "dataset_version_id": dataset_version_id}
    try:
        attach_experiment_links(
            storage_root=storage_root,
            experiment_id=experiment_id,
            linked_datasets=[dataset_ref],
            updated_by_user_id=actor,
        )
        note_result = append_experiment_note(
            storage_root=storage_root,
            experiment_id=experiment_id,
            payload={
                "body": payload.get("note")
                or (
                    "Accepted failure-replay dataset version "
                    f"{dataset_id}.{dataset_version_id} for the next experiment iteration."
                ),
                "author_name": actor,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    experiment = repository.get_experiment(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail=f"Experiment not found: {experiment_id}")

    return {
        "experiment_id": experiment_id,
        "accepted_dataset": dataset_ref,
        "note_id": note_result.note_id,
        "experiment": experiment,
        "handoff": handoff,
        "next_actions": [
            "launch_training_run_with_linked_dataset_version",
            "register_checkpoint_as_model_version",
            "rerun_source_eval_suite",
            "compare_new_model_to_source_model_versions",
        ],
    }
