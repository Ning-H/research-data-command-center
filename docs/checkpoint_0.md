# Checkpoint 0: Planning, Menu, Contract, and Foundation Scaffold

## What Happens Next

After owner confirmation, Phase 1 starts with detailed research/design plans for the three specialist agents. No product-area implementation starts until the relevant data-source, schema, API, UI, and checkpoint plans are confirmed.

## Confirmed Product Direction

- Product name: Research Data Command Center.
- Product position: researcher-facing internal data platform for AI research workflows.
- Final navigation:

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

- Dataset lineage belongs inside Datasets.
- Run lineage belongs inside Runs.
- Model lineage belongs inside Models & Evaluations.
- API and SDK documentation belongs under Docs, not as a top-level product pillar.

## Specialist Agents

- Dataset Agent: Catalog, Register Dataset, Records Explorer, Quality, Versions, Lineage & Usage.
- Runs Agent: Active Runs, Run History, Run Detail, Metrics, Compute, Checkpoints, Lineage.
- Models & Evaluations Agent: Model Registry, Evaluation Dashboard, Compare Models, Checkpoint Comparison, Failure Explorer, Regression Analysis, Model Lineage.

## Data Decisions

- Core dataset records: `PUBLIC_REAL` public datasets, to be selected in Dataset Checkpoint 1.
- Dataset quality/profile outputs: `GENERATED_REAL` local computed outputs, designed in Dataset Checkpoint 2.
- Training metrics/checkpoints: `GENERATED_REAL` small-model runs when practical, designed in Runs Checkpoint 1.
- Compute telemetry: `SYNTHETIC_REALISTIC` constrained telemetry with documented physics/causality rules unless real telemetry is available, designed in Runs Checkpoint 1.
- Eval cases: `PUBLIC_REAL` public eval datasets/tasks, designed in Models/Evals Checkpoint 1.
- Eval outputs/scores: `GENERATED_REAL` real model outputs from small models where practical, designed in Models/Evals Checkpoint 1.
- Synthetic metadata is allowed only for owner/team names, notes, labels, permissions, gate decisions, review state, and similar non-core fields.

## Schema/Contract Usage

The scaffold defines the canonical keys, shared status enums, storage layers, and minimum shared table contracts in:

- `docs/shared_data_contract.md`
- `shared/research_command_center_contract/keys.py`
- `shared/research_command_center_contract/enums.py`
- `shared/research_command_center_contract/tables.py`

All agents must consume these definitions rather than inventing new shared identifiers.

## Open Questions / Assumptions

- `experiment_id` is included as a table key because the lineage spine requires `experiment --< run`; it was not listed in the canonical key list but is needed to avoid an unnamed experiment foreign key.
- `dataset_candidate_id` is included because the failure-to-dataset loop requires a concrete candidate entity; it was present in the lineage spine but not in the canonical key list.
- `deployment` and `inference_traffic` remain later-phase concepts and are not scaffolded for v1 foundation.

## Explicit Ask

Confirm to proceed with the three agent research/design plans, or adjust the shared contract/scaffold first?
