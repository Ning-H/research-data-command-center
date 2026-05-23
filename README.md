# Research Data Command Center

A researcher-facing platform for tracing the AI research data lifecycle:

```text
Register dataset -> validate & version -> launch/ingest training run
-> monitor metrics & checkpoints -> register candidate model -> evaluate
-> compare versions -> inspect failures -> save failures as dataset candidates
-> create next dataset version -> loop
```

This repo is currently at **Phase 0: Planning and Foundation**. Agent feature work is intentionally blocked until Checkpoint 0 confirms the product direction, final menu, shared contract, and scaffold.

## Product Navigation

```text
Research Data Command Center
├── Home
├── Datasets
├── Runs
├── Models & Evaluations
├── Workspace
├── Docs
└── Settings
```

API and SDK references live under Docs. Dataset lineage belongs inside Datasets, run lineage inside Runs, and model lineage inside Models & Evaluations.

## V1 Stack

- Frontend: React / Next.js
- Backend: FastAPI
- Processing: Python, Pandas/Polars, DuckDB
- Analytical storage: Parquet + DuckDB
- App metadata: Postgres
- Raw/object storage: local object-store-style folders
- SDK: Python package wrapping the API

## Phase 0 Contents

- Master agent guidelines: `docs/ai_agent_build_guidelines.md`
- Shared contract docs: `docs/shared_data_contract.md`
- Checkpoint 0 brief: `docs/checkpoint_0.md`
- Canonical keys/enums/table contracts: `shared/research_command_center_contract/`
- FastAPI skeleton: `backend/app/`
- Python SDK skeleton: `sdk/research_command_center_sdk/`
- Next.js placeholder app metadata: `frontend/package.json`
- Storage layer directories: `storage/`

## Local Validation

```bash
uv run --python 3.13 --with pytest python -m pytest
```

## Dataset Walking Skeleton

After Dataset Checkpoint 2 approval, the first ingestion path normalizes Databricks Dolly 15k into local Parquet and registers DuckDB views:

```bash
uv run --python 3.13 python scripts/ingest_dolly.py --limit 100
```

Additional sampled public dataset ingestors:

```bash
uv run --python 3.13 python scripts/ingest_public_dataset.py hh-rlhf --limit 100
uv run --python 3.13 python scripts/ingest_public_dataset.py samsum --limit 100
```

Generated raw, object-store, Parquet, and DuckDB files are written under `storage/` and intentionally ignored by git.

Next product work should continue through the checkpoint flow before broadening beyond this dataset foundation.
