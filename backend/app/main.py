from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dataset_candidates.api import router as dataset_candidates_router
from app.datasets.api import jobs_router as dataset_ingestion_jobs_router
from app.datasets.api import router as datasets_router
from app.evaluations.api import router as evaluations_router
from app.experiments.api import router as experiments_router
from app.models.api import router as models_router
from app.research_programs.api import router as research_programs_router
from app.runs.api import checkpoints_router, router as runs_router
from research_command_center_contract import (
    ANALYTICAL_TABLES,
    APP_METADATA_TABLES,
    CANONICAL_KEYS,
    FOUNDATION_KEYS,
)

app = FastAPI(
    title="Research Data Command Center API",
    version="0.1.0",
    description="Phase 0 foundation API exposing the shared contract.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets_router)
app.include_router(dataset_ingestion_jobs_router)
app.include_router(research_programs_router)
app.include_router(experiments_router)
app.include_router(runs_router)
app.include_router(checkpoints_router)
app.include_router(models_router)
app.include_router(evaluations_router)
app.include_router(dataset_candidates_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "0-foundation"}


@app.get("/contract")
def contract() -> dict[str, object]:
    return {
        "canonical_keys": CANONICAL_KEYS,
        "foundation_keys": FOUNDATION_KEYS,
        "app_metadata_tables": [table.__dict__ for table in APP_METADATA_TABLES],
        "analytical_tables": [table.__dict__ for table in ANALYTICAL_TABLES],
    }
