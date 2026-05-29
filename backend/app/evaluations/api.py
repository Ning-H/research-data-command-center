from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.evaluations.lifecycle import register_eval_run, register_eval_suite, update_eval_failure_review
from app.evaluations.repository import EvaluationRepository
from app.evaluations.schemas import EvalRunCreatePayload, EvalSuiteCreatePayload

router = APIRouter(tags=["evaluations"])


def get_evaluation_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


def get_evaluation_repository() -> EvaluationRepository:
    storage_root = get_evaluation_storage_root()
    return EvaluationRepository(
        duckdb_path=Path(settings.duckdb_path),
        storage_root=storage_root,
    )


@router.post("/eval-suites")
def create_eval_suite(
    payload: EvalSuiteCreatePayload,
    storage_root: Annotated[Path, Depends(get_evaluation_storage_root)],
) -> dict[str, Any]:
    try:
        result = register_eval_suite(
            storage_root=storage_root,
            payload=payload.model_dump(exclude_none=True),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "eval_suite_id": result.eval_suite_id,
        "case_count": result.case_count,
        "status": result.status,
    }


@router.get("/eval-suites")
def list_eval_suites(
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_eval_suites(limit=limit, offset=offset),
        "limit": limit,
        "offset": offset,
    }


@router.get("/eval-suites/{eval_suite_id}")
def get_eval_suite(
    eval_suite_id: int,
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
) -> dict[str, Any]:
    suite = repository.get_eval_suite(eval_suite_id)
    if suite is None:
        raise HTTPException(status_code=404, detail=f"Eval suite not found: {eval_suite_id}")
    return suite


@router.post("/eval-runs")
def create_eval_run(
    payload: EvalRunCreatePayload,
    storage_root: Annotated[Path, Depends(get_evaluation_storage_root)],
) -> dict[str, Any]:
    try:
        result = register_eval_run(
            storage_root=storage_root,
            payload=payload.model_dump(exclude_none=True),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "eval_run_id": result.eval_run_id,
        "eval_suite_id": result.eval_suite_id,
        "model_version_id": result.model_version_id,
        "output_count": result.output_count,
        "failure_count": result.failure_count,
        "status": result.status,
    }


@router.get("/eval-runs")
def list_eval_runs(
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
    program_id: int | None = None,
    experiment_id: int | None = None,
    eval_suite_id: int | None = None,
    model_version_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_eval_runs(
            program_id=program_id,
            experiment_id=experiment_id,
            eval_suite_id=eval_suite_id,
            model_version_id=model_version_id,
            limit=limit,
            offset=offset,
        ),
        "limit": limit,
        "offset": offset,
        "filters": {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "eval_suite_id": eval_suite_id,
            "model_version_id": model_version_id,
        },
    }


@router.get("/eval-runs/{eval_run_id}")
def get_eval_run(
    eval_run_id: int,
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
) -> dict[str, Any]:
    eval_run = repository.get_eval_run(eval_run_id)
    if eval_run is None:
        raise HTTPException(status_code=404, detail=f"Eval run not found: {eval_run_id}")
    return eval_run


@router.get("/eval-failures")
def list_eval_failures(
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
    program_id: int | None = None,
    experiment_id: int | None = None,
    eval_run_id: int | None = None,
    model_version_id: int | None = None,
    dataset_id: int | None = None,
    dataset_version_id: int | None = None,
    failure_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_eval_failures(
            program_id=program_id,
            experiment_id=experiment_id,
            eval_run_id=eval_run_id,
            model_version_id=model_version_id,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            failure_type=failure_type,
            severity=severity,
            status=status,
            limit=limit,
            offset=offset,
        ),
        "limit": limit,
        "offset": offset,
        "filters": {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "eval_run_id": eval_run_id,
            "model_version_id": model_version_id,
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "failure_type": failure_type,
            "severity": severity,
            "status": status,
        },
    }


@router.get("/eval-failures/{eval_failure_id}")
def get_eval_failure(
    eval_failure_id: int,
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
) -> dict[str, Any]:
    failure = repository.get_eval_failure(eval_failure_id)
    if failure is None:
        raise HTTPException(status_code=404, detail=f"Eval failure not found: {eval_failure_id}")
    return failure


@router.patch("/eval-failures/{eval_failure_id}")
def update_eval_failure(
    eval_failure_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_evaluation_storage_root)],
) -> dict[str, Any]:
    try:
        update_eval_failure_review(
            storage_root=storage_root,
            eval_failure_id=eval_failure_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    repository = EvaluationRepository(
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
        storage_root=storage_root,
    )
    failure = repository.get_eval_failure(eval_failure_id)
    if failure is None:
        raise HTTPException(status_code=404, detail=f"Eval failure not found: {eval_failure_id}")
    return failure


@router.get("/evaluations/summary")
def get_evaluation_summary(
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
    program_id: int | None = None,
    experiment_id: int | None = None,
    eval_suite_id: int | None = None,
    model_version_id: int | None = None,
) -> dict[str, Any]:
    return repository.evaluation_summary(
        program_id=program_id,
        experiment_id=experiment_id,
        eval_suite_id=eval_suite_id,
        model_version_id=model_version_id,
    )


@router.get("/experiments/{experiment_id}/evaluation-summary")
def get_experiment_evaluation_summary(
    experiment_id: int,
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
) -> dict[str, Any]:
    return repository.evaluation_summary(experiment_id=experiment_id)


@router.get("/failure-library")
def list_failure_library(
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
    program_id: int | None = None,
    experiment_id: int | None = None,
    model_version_id: int | None = None,
    dataset_id: int | None = None,
    dataset_version_id: int | None = None,
    failure_type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_eval_failures(
            program_id=program_id,
            experiment_id=experiment_id,
            model_version_id=model_version_id,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            failure_type=failure_type,
            severity=severity,
            status=status,
            limit=limit,
            offset=offset,
        ),
        "filters": {
            "program_id": program_id,
            "experiment_id": experiment_id,
            "model_version_id": model_version_id,
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "failure_type": failure_type,
            "severity": severity,
            "status": status,
        },
        "limit": limit,
        "offset": offset,
    }


@router.get("/failure-library/summary")
def get_failure_library_summary(
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
    program_id: int | None = None,
    experiment_id: int | None = None,
    model_version_id: int | None = None,
    dataset_id: int | None = None,
) -> dict[str, Any]:
    return repository.failure_summary(
        program_id=program_id,
        experiment_id=experiment_id,
        model_version_id=model_version_id,
        dataset_id=dataset_id,
    )


@router.get("/failure-library/{eval_failure_id}")
def get_failure_library_item(
    eval_failure_id: int,
    repository: Annotated[EvaluationRepository, Depends(get_evaluation_repository)],
) -> dict[str, Any]:
    failure = repository.get_eval_failure(eval_failure_id)
    if failure is None:
        raise HTTPException(status_code=404, detail=f"Eval failure not found: {eval_failure_id}")
    return failure
