# Checkpoint 0: Contract + Foundation Scaffold

## What Happens Next

After owner confirmation, Phase 1 starts with Agent 1A only: Dataset Steward research and plan. No Dataset feature implementation starts until the 1A data-source, schema, quality, and versioning plan is confirmed.

## Data Decisions

- Core dataset records: Priority 1 public datasets, to be selected in Agent 1A.
- Dataset quality/profile outputs: Priority 2 local computed outputs, designed in Agent 1A.
- Training metrics/checkpoints: Priority 2 real small-model runs, designed in Agent 2A.
- Compute telemetry: Priority 3 constrained synthetic telemetry with documented physics/causality rules, designed in Agent 2A.
- Eval cases: Priority 1 public eval datasets/tasks, designed in Agent 3A.
- Eval outputs/scores: Priority 2 real model outputs from small models, designed in Agent 3A.
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

Confirm to proceed with Phase 1A Dataset Steward research, or adjust the shared contract/scaffold first?
