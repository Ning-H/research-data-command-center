# Research Data Command Center

A lineage-first research operations platform for tracing the AI research lifecycle:

```text
Research Program -> Hypothesis -> Data Assets -> Data Mixtures -> Experiments
-> Training Runs -> Checkpoints -> Model Versions -> Evaluation Runs
-> Inference Traces -> Failure Cases -> Dataset Candidates -> Next Experiment
```

The product question is:

> What changed, why did model behavior change, which data/run/checkpoint caused it, and what should we try next?

The project is currently a working local research-ops prototype. It does not
train models itself or own real-time production monitoring; researchers train
where they already train, and this system captures the lineage around programs,
datasets, experiments, runs, checkpoints, model versions, evaluation results,
failures, and dataset-iteration candidates.

## Current Status

As of the latest local check:

- Branch: `main`, aligned with `origin/main`
- Latest commit: `1e4385c Add dataset versioning lifecycle, evaluations module, and research programs UI`
- Backend validation: `26 passed`
- Frontend validation: `npm run build` passes
- Local backend: `http://127.0.0.1:8000/health`
- Local frontend: `http://localhost:3000`
- Evaluation loop demo data: `7` eval runs, `22` failures, `22` dataset candidates after the latest local lifecycle seed
- Verified UI flow: failure review -> dataset candidate approval -> candidate-derived dataset version publish

One local-state caveat: generated artifacts exist under `storage/object_store`
and `storage/parquet`, but the live metadata API can still return empty lists if
Postgres is unseeded or pointed at a fresh database. Re-run one of the seed or
lifecycle scripts when you want a populated demo session.

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
lifecycle: collect educational/coding data, define study-guide quality rubrics,
run model variants, compare generated documents, capture failures such as
missing topics or shallow explanations, and turn those failures into the next
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

## Working Slices

- Research Programs: registry/detail/create/edit flow, program notes, and links into datasets/runs.
- Data Assets: public dataset ingestion, version registration, draft/publish lifecycle, records, schema, quality, lineage, and access events.
- Experiments: experiment registration, updates, and appendable notes.
- Training Runs: external API/SDK run registration, raw metric append, checkpoint append, completion, and run lineage.
- Models & Checkpoints: cross-run checkpoint search, checkpoint-to-model-version registration, model detail, model lineage, and model comparison.
- Evaluations: eval-suite registration, eval-run registration, model-level eval lookup, experiment evaluation summary, aggregate evaluation summary, and an API-backed evaluation dashboard.
- Failure Library: evaluation-failure browsing, filtering, summaries, detail lookup, lineage inspection, and candidate creation.
- Dataset Candidates: convert failures into dataset candidates, review candidate status, inspect dataset iteration summaries, and publish candidate-derived dataset versions.
- Frontend Shell: routes exist for the major product areas, including research programs, datasets, experiments, runs, models, evaluations, failure library, dataset iterations, workspace, docs, and settings.

## Local Development

Install frontend dependencies once:

```bash
cd frontend
npm install
```

Run the backend:

```bash
PYTHONPATH=backend uv run --python 3.13 uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run the frontend:

```bash
cd frontend
npm run dev
```

Validate the backend:

```bash
uv run --python 3.13 --with pytest python -m pytest
```

Validate the frontend:

```bash
cd frontend
npm run build
```

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

Generated raw, object-store, Parquet, and DuckDB files are written under
`storage/` and intentionally ignored by git.

## Demo Data

Useful local scripts:

```bash
uv run --python 3.13 python scripts/seed_demo_runs.py
uv run --python 3.13 python scripts/run_study_material_full_lifecycle.py
```

The full lifecycle script is the most complete demo path for the current product
story. It creates a study-material research program path with datasets,
experiments, training runs, checkpoints, evaluation suites/runs, failures, and
dataset candidates.

After running it locally, open:

```text
http://localhost:3000/evaluations
http://localhost:3000/failure-library
http://localhost:3000/dataset-iterations
```

The intended demo path is:

```text
Evaluations -> Failure Library -> Failure Detail -> Save Candidate
-> Dataset Iterations -> Approve Candidate -> Publish Dataset Version
```

## Next Build Slice

The strongest next slice is to connect the newly published dataset version back
into the next experiment/run decision: show which approved failures created the
version, which experiment should consume it, and whether the next model version
improves against the same rubric.
