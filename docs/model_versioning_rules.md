# Model Versioning Rules

Status: **Models working rule**

Model versions are immutable research artifacts. A model version is the stable
thing that evaluations, failure cases, dataset candidates, deployments, and
research decisions attach to. The platform can change review state and add
evidence around a model version, but it must not silently change what model
artifact that version means.

## Identifier Meanings

- `model_id` identifies a model family or logical model line, such as
  `python-algorithm-study-guide-policy`.
- `model_version_id` identifies one immutable model artifact record.
- `checkpoint_id` identifies the source checkpoint for current v1 model
  versions.
- `run_id`, `dataset_id`, `dataset_version_id`, and `run_config_id` explain the
  training lineage that produced the checkpoint.
- `artifact_uri` points to the model/checkpoint artifact. The platform stores
  metadata and lineage, not the training job itself.

## Current V1 Creation Rule

In v1, a trained candidate model version is created by promoting a checkpoint:

```text
dataset_version -> run_config -> run -> checkpoint -> model_version
```

Promotion may happen from the UI or from the SDK. Both should call the same API:

```text
POST /models/register-from-checkpoint
```

The researcher provides review context:

```text
checkpoint_id
model_name
model_version_name
owner_user_id
intended_use
promotion_reason
promotion_notes
expected_eval_suite_ids
```

The platform derives lineage from the checkpoint:

```text
run_id
program_id
experiment_id
dataset_id
dataset_version_id
run_config_id
artifact_uri
metrics_snapshot
source_checkpoint_step
base_model_name
```

The UI should make promotion convenient for human review. The SDK should make
promotion convenient for notebooks, scripts, cluster jobs, and CI-style
evaluation pipelines.

## When Version Changes

Create a new `model_version_id` when the model's behavior, artifact identity, or
reproducibility lineage changes.

Create a new model version when:

- A different checkpoint is promoted.
- The weights or artifact content changes.
- The `artifact_uri` points to a different artifact revision.
- The dataset version used for training changes.
- The run config changes in a way that can affect model behavior.
- The base model or parent model version changes.
- Tokenizer, adapter, LoRA, quantization, or inference-time model config changes
  in a way that can affect outputs.
- Multiple checkpoints or adapters are merged into a new artifact.
- A model is distilled, exported, converted, or fine-tuned from another model
  version.
- An externally hosted model is recorded at a different provider revision,
  snapshot, or pinned release.

Do not create a new model version when only review metadata changes.

Keep the same model version when:

- New evaluations are run against the same artifact.
- Scores, failures, regressions, or dataset candidates are attached.
- Status changes, such as `candidate`, `registered`, `promoted`, or `archived`.
- Intended use, notes, owners, tags, promotion rationale, or review decisions are
  updated.
- A deployment, dashboard, or UI label changes without changing the model
  artifact or behavior-affecting config.
- An artifact is copied to a new storage location only as a byte-identical
  mirror, and the original lineage remains valid.

## Metadata Mutability

Immutable fields should not be rewritten after registration:

```text
model_version_id
checkpoint_id
run_id
dataset_id
dataset_version_id
run_config_id
artifact_uri
metrics_snapshot
source_checkpoint_step
base_model_name
created_at
created_by_user_id
```

Mutable review fields may change through explicit review actions or append-only
events:

```text
status
intended_use
promotion_reason
promotion_notes
expected_eval_suite_ids
tags
owner or steward metadata
```

When possible, review changes should be recorded as events instead of in-place
rewrites so researchers can understand who changed a decision and why.

## Future Source Types

Checkpoint promotion is the only implemented v1 creation path for trained model
versions. Future phases may add additional source types, but they should be
explicit fields rather than loose artifact uploads.

Possible future `source_type` values:

```text
checkpoint
external_model
parent_model_version
merged_model_versions
manual_baseline
```

Adding these source types requires a shared-contract checkpoint because it
changes lineage rules, API payloads, and UI expectations.

## UI Split Rules

The Training Runs & Checkpoints UI owns checkpoint review. The Models UI owns
model-version review after promotion:

- Promote from a ranked checkpoint row or checkpoint detail page.
- Show the exact run, dataset version, training config, metrics snapshot, and
  artifact URI before promotion.
- Require or strongly encourage intended use and promotion reason.
- After promotion, route to the immutable model version detail page.
- Show model versions separately from unpromoted checkpoints.
- Treat eval results and failures as evidence attached to a model version, not
  as edits to the model version itself.

## SDK Rules

The SDK should expose the same promotion action used by the UI:

```python
client.register_model_from_checkpoint(
    checkpoint_id=7002,
    model_name="python-algorithm-study-guide-policy",
    model_version_name="candidate-checkpoint-7002",
    intended_use="Candidate model version for rubric evaluation.",
    promotion_reason="Highest ranked checkpoint for the selected dataset and metric.",
)
```

SDK promotion should be preferred when a training script, notebook, or workflow
already knows which checkpoint passed its local gate. UI promotion should be
preferred when a researcher needs to compare checkpoints before deciding.
