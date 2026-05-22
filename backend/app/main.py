from fastapi import FastAPI

from research_command_center_contract import ANALYTICAL_TABLES, APP_METADATA_TABLES, CANONICAL_KEYS

app = FastAPI(
    title="Research Data Command Center API",
    version="0.1.0",
    description="Phase 0 foundation API exposing the shared contract.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "0-foundation"}


@app.get("/contract")
def contract() -> dict[str, object]:
    return {
        "canonical_keys": CANONICAL_KEYS,
        "app_metadata_tables": [table.__dict__ for table in APP_METADATA_TABLES],
        "analytical_tables": [table.__dict__ for table in ANALYTICAL_TABLES],
    }
