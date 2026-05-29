# Models and Checkpoint Promotion

## Product Rule

Researchers train outside the platform and save checkpoints during the run. A
checkpoint can become a model version only through a promotion event.

Detailed versioning and immutability rules live in
[`docs/model_versioning_rules.md`](model_versioning_rules.md).

The researcher provides:

```text
checkpoint_id
model_name
model_version_name
owner_user_id
intended_use
promotion_reason
promotion_notes
```

The platform derives:

```text
run_id
dataset_id
dataset_version_id
run_config_id
artifact_uri
metrics_snapshot
```

That keeps lineage governed by platform metadata instead of free-form user
entry.

## API

```text
POST /models/register-from-checkpoint
GET /models
GET /models/{model_version_id}
GET /models/{model_version_id}/lineage
```

Example promotion payload:

```json
{
  "checkpoint_id": 7002,
  "model_name": "dolly-pytorch-classifier",
  "model_version_name": "candidate-checkpoint-7002",
  "owner_user_id": "user_demo_owner",
  "intended_use": "Candidate model version for instruction classification evaluation.",
  "promotion_reason": "Highest ranked checkpoint for the selected dataset, trainer, and metric."
}
```

## Storage Rule

For v1, the source of truth is the immutable `model_versions` metadata table in
Parquet/DuckDB. The row includes explicit lineage keys:

```text
model_id
model_version_id
checkpoint_id
run_id
dataset_id
dataset_version_id
```

The model artifact URI points to the checkpoint artifact produced by the
training job. The platform also writes a small object-store-style manifest
under:

```text
storage/object_store/models/model_id={model_id}/model_version_id={model_version_id}/registration_manifest.json
```

## Lineage

The model detail page and API expose:

```text
dataset_version -> run -> checkpoint -> model_version
```

Evaluation runs should attach to `model_version_id`, not directly to loose
checkpoint paths.
