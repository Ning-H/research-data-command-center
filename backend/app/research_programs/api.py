from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.research_programs.lifecycle import (
    append_research_program_note,
    delete_research_program_note,
    register_research_program,
    update_research_program,
)
from app.research_programs.repository import ResearchProgramRepository

router = APIRouter(prefix="/research-programs", tags=["research-programs"])


def get_research_program_storage_root() -> Path:
    return Path(settings.raw_storage_root).parent


def get_research_program_repository() -> ResearchProgramRepository:
    storage_root = get_research_program_storage_root()
    return ResearchProgramRepository(
        duckdb_path=Path(settings.duckdb_path),
        storage_root=storage_root,
    )


@router.get("")
def list_research_programs(
    repository: Annotated[ResearchProgramRepository, Depends(get_research_program_repository)],
    status: str | None = None,
    researcher_name: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": repository.list_programs(
            status=status,
            researcher_name=researcher_name,
            tag=tag,
            q=q,
            limit=limit,
            offset=offset,
        ),
        "limit": limit,
        "offset": offset,
        "filters": {"status": status, "researcher_name": researcher_name, "tag": tag, "q": q},
    }


@router.post("")
def create_research_program(
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_research_program_storage_root)],
) -> dict[str, Any]:
    try:
        result = register_research_program(storage_root=storage_root, payload=payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "program_id": result.program_id,
        "program_name": result.program_name,
        "status": result.status,
        "researcher_names": result.researcher_names,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


@router.get("/{program_id}")
def get_research_program(
    program_id: int,
    repository: Annotated[ResearchProgramRepository, Depends(get_research_program_repository)],
) -> dict[str, Any]:
    program = repository.get_program(program_id)
    if program is None:
        raise HTTPException(status_code=404, detail=f"Research program not found: {program_id}")
    return program


@router.patch("/{program_id}")
def patch_research_program(
    program_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_research_program_storage_root)],
    repository: Annotated[ResearchProgramRepository, Depends(get_research_program_repository)],
) -> dict[str, Any]:
    try:
        update_research_program(storage_root=storage_root, program_id=program_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    program = repository.get_program(program_id)
    if program is None:
        raise HTTPException(status_code=404, detail=f"Research program not found: {program_id}")
    return program


@router.post("/{program_id}/notes")
def append_note(
    program_id: int,
    payload: dict[str, Any],
    storage_root: Annotated[Path, Depends(get_research_program_storage_root)],
    repository: Annotated[ResearchProgramRepository, Depends(get_research_program_repository)],
) -> dict[str, Any]:
    try:
        result = append_research_program_note(
            storage_root=storage_root,
            program_id=program_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    program = repository.get_program(program_id)
    if program is None:
        raise HTTPException(status_code=404, detail=f"Research program not found: {program_id}")
    return {
        "program_id": result.program_id,
        "note_id": result.note_id,
        "notes": result.notes,
        "updated_at": result.updated_at,
        "program": program,
    }


@router.delete("/{program_id}/notes/{note_id}")
def delete_note(
    program_id: int,
    note_id: int,
    storage_root: Annotated[Path, Depends(get_research_program_storage_root)],
    repository: Annotated[ResearchProgramRepository, Depends(get_research_program_repository)],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        result = delete_research_program_note(
            storage_root=storage_root,
            program_id=program_id,
            note_id=note_id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    program = repository.get_program(program_id)
    if program is None:
        raise HTTPException(status_code=404, detail=f"Research program not found: {program_id}")
    return {
        "program_id": result.program_id,
        "deleted_note_id": result.note_id,
        "notes": result.notes,
        "updated_at": result.updated_at,
        "program": program,
    }
