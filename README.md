# Research Data Command Center

A researcher-facing platform for tracing the AI research data lifecycle:

```text
Register dataset -> validate & version -> launch/ingest training run
-> monitor metrics & checkpoints -> register candidate model -> evaluate
-> compare versions -> inspect failures -> save failures as dataset candidates
-> create next dataset version -> loop
```

This repo is currently at **Phase 0: Foundation**. Agent feature work is intentionally blocked until Checkpoint 0 confirms the shared contract and scaffold.

## V1 Stack

- Frontend: React / Next.js
- Backend: FastAPI
- Processing: Python, Pandas/Polars, DuckDB
- Analytical storage: Parquet + DuckDB
- App metadata: Postgres
- Raw/object storage: local object-store-style folders
- SDK: Python package wrapping the API

## Phase 0 Contents

- Shared contract docs: `docs/shared_data_contract.md`
- Checkpoint 0 brief: `docs/checkpoint_0.md`
- Canonical keys/enums/table contracts: `shared/research_command_center_contract/`
- FastAPI skeleton: `backend/app/`
- Python SDK skeleton: `sdk/research_command_center_sdk/`
- Next.js placeholder app metadata: `frontend/package.json`
- Storage layer directories: `storage/`

## Local Validation

```bash
python -m pytest
```

Feature implementation begins only after the owner confirms Checkpoint 0.
