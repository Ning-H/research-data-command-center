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

- Branch: `main`, published directly to `origin/main`
- Backend validation: `27 passed`
- Frontend validation: `npm run build` passes
- Local backend: `http://127.0.0.1:8000/health`
- Local frontend: `http://localhost:3000`
- Current product checkpoint: data asset registration, experiment planning, run/checkpoint inspection, model review, evaluation ingestion, failure review, and dataset-iteration handoff are all represented in the API/UI.
- Verified lifecycle flow: failure review -> dataset candidate approval -> candidate-derived dataset version publish -> next experiment planning.

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
├── Training Runs & Checkpoints
├── Models
├── Evaluations
├── Inference Observability
├── Failure Library
├── Dataset Iterations
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
- Model registry direction: `docs/model_registry.md`
- Model versioning rules: `docs/model_versioning_rules.md`
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
- Experiments: experiment registry, create/detail/edit screens, notes, dataset/run/model links, and next-run planning context.
- Training Runs & Checkpoints: external API/SDK run registration, raw metric append, checkpoint append, completion, run lineage, run filters, checkpoint comparison, and cross-run checkpoint ranking.
- Models: checkpoint-to-model-version promotion, model detail, model lineage, review context, evaluation readiness, filtering, and model comparison.
- Evaluations: eval-suite registration, SDK-style eval-run submission, idempotent external eval IDs, model-level eval lookup, experiment evaluation summary, aggregate evaluation summary, and an API-backed evaluation dashboard.
- Failure Library: evaluation-failure browsing, filtering, summaries, detail lookup, lineage inspection, review status/root-cause notes, and candidate creation.
- Dataset Candidates: convert failures into dataset candidates, review candidate status, inspect dataset iteration summaries, and publish candidate-derived dataset versions for the next experiment.
- Frontend Shell: routes exist for the major product areas, including research programs, datasets, experiments, runs, models, evaluations, failure library, dataset iterations, docs, and settings.

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
uv run --python 3.13 python scripts/run_sdk_sample_eval.py
```

The full lifecycle script is the most complete demo path for the current product
story. It creates a study-material research program path with datasets,
experiments, training runs, checkpoints, evaluation suites/runs, failures, and
dataset candidates. The SDK sample eval script submits a repeatable eval run
against the local API using the Python SDK and an external eval-run ID.

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

The strongest next slice is to close the loop after a candidate-derived dataset
version is published: make the recommended next experiment/run explicit, attach
the new run to the version that triggered it, and show whether the next model
version improves against the same rubric.
