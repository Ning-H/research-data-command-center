# Research Data Command Center

A lineage-first research operations platform for tracing the AI research lifecycle:

```text
Research Program -> Hypothesis -> Data Assets -> Data Mixtures -> Experiments
-> Training Runs -> Checkpoints -> Model Versions -> Evaluation Runs
-> Inference Traces -> Failure Cases -> Dataset Candidates -> Next Experiment
```

The product question is:

> What changed, why did model behavior change, which data/run/checkpoint caused it, and what should we try next?

The repo now has working foundation slices for data assets, training run ingestion, checkpoint search, and checkpoint-to-model registration. The next expansion should attach evaluations, inference traces, failure cases, and dataset candidates to the same lineage spine.

## First Research Program

The seed program is based on a real user experience: asking a frontier model to
generate Python algorithms study material should be a standard educational task,
but the final document came back shallow, uneven, and hard to use. It produced a
lot of fluent text, but did not create a systematic learning artifact with clear
coverage, deep explanations, examples, LeetCode-style practice links, and a
progression from fundamentals to harder patterns.

That motivates the first research program:

> Improve structured technical study-material generation for Python algorithms
> interview preparation.

This is a useful research-data-platform demo because it touches the whole
lifecycle: collect public educational/coding data, define study-guide quality
rubrics, run model variants, compare generated documents, capture failures such
as missing topics or shallow explanations, and turn those failures into the next
dataset version.

## Product Navigation

```text
Research Data Command Center
├── Home
├── Research Programs
├── Data Assets
├── Experiments
├── Training Runs
├── Models & Checkpoints
├── Evaluations
├── Inference Observability
├── Failure Library
├── Dataset Iterations
├── Workspace
├── Docs
└── Settings
```

API and SDK references live under Docs. Product surfaces should answer at least one of:

- What research goal are we working on?
- What hypothesis are we testing?
- What data was used?
- What changed between runs?
- Which checkpoint/model came from which run?
- How did the model perform?
- Where did it fail?
- What dataset/version should be created next?

## V1 Stack

- Frontend: React / Next.js
- Backend: FastAPI
- Processing: Python, Pandas/Polars, DuckDB
- Analytical storage: Parquet + DuckDB
- App metadata: Postgres
- Raw/object storage: local object-store-style folders
- SDK: Python package wrapping the API

## Current Contents

- Master agent guidelines: `docs/ai_agent_build_guidelines.md`
- Research lifecycle direction: `docs/research_lifecycle_command_center.md`
- Shared contract docs: `docs/shared_data_contract.md`
- Checkpoint 0 brief: `docs/checkpoint_0.md`
- Canonical keys/enums/table contracts: `shared/research_command_center_contract/`
- FastAPI backend: `backend/app/`
- Python SDK: `sdk/research_command_center_sdk/`
- Next.js app: `frontend/`
- Storage layer directories: `storage/`

## Local Validation

```bash
uv run --python 3.13 --with pytest python -m pytest
```

## Working Slices

- Data Assets: public dataset ingestion, schema/quality/profile views, sample records, and lineage.
- Training Runs: external API/SDK run registration, raw metric append, checkpoint append, and run detail.
- Models & Checkpoints: cross-run checkpoint search and checkpoint-to-model-version registration.

## Dataset Walking Skeleton

The first ingestion path normalizes Databricks Dolly 15k into local Parquet and registers DuckDB views:

```bash
uv run --python 3.13 python scripts/ingest_dolly.py --limit 100
```

Additional sampled public dataset ingestors:

```bash
uv run --python 3.13 python scripts/ingest_public_dataset.py hh-rlhf --limit 100
uv run --python 3.13 python scripts/ingest_public_dataset.py samsum --limit 100
uv run --python 3.13 python scripts/ingest_public_dataset.py squad --limit 100
uv run --python 3.13 python scripts/ingest_public_dataset.py humaneval --limit 100
```

Generated raw, object-store, Parquet, and DuckDB files are written under `storage/` and intentionally ignored by git.

## Next Build Slice

Build the study-material evaluation slice against `model_version_id`, then save
failed generated sections into the Failure Library and dataset candidate
workflow.
