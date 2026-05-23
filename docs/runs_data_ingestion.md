# Runs Data Ingestion

Status: **Runs Agent working rule**

The platform does not launch or monitor training jobs directly in v1.

Researchers train wherever they already train:

- local machine
- notebook
- GPU workstation
- cluster
- cloud training job

Their script calls the Research Data Command Center API/SDK to save:

- `dataset_id` and `dataset_version_id` used
- run config
- raw training metric events
- checkpoint metadata and checkpoint URI
- later model version metadata
- later eval outputs and failures

The platform stores the raw run event stream and normalizes it into:

- `training_metrics`
- `compute_metrics`
- `checkpoints`
- run health summary
- lineage from dataset version to run config to run to checkpoints

## Run Registration Rule

Every training run must be registered before raw run data is appended. The platform
generates the `run_id` as an integer sequence (`1`, `2`, `3`, ...). Researchers do
not choose or rename `run_id`.

Training data must already be registered in this platform before it can be used by
a run. That is the governance boundary: the platform can only control data
quality, privacy, provenance, and lineage for datasets it knows about.

The run registration request must include both:

```text
dataset_id
dataset_version_id
```

Together, `dataset_id` and `dataset_version_id` identify the governed training
dataset version and the Parquet record partitions the researcher should connect
to for training. `dataset_id` identifies the dataset family; `dataset_version_id`
identifies the exact immutable version used by the run.

Minimum registration context:

```text
run_name
dataset_id
dataset_version_id
base_model_name or parent_model_version_id
training_task
research_intent
owner_user_id
training_environment
run_config
artifact_root_uri
```

After registration, researchers append run data to the existing `run_id`:

```text
POST /runs/register -> returns run_id
POST /runs/{run_id}/events -> appends raw metric/log events
POST /runs/{run_id}/checkpoints -> appends checkpoint metadata
POST /runs/{run_id}/complete -> closes the run as completed, failed, or killed
```

Same `run_id`:

- same registered run
- same objective
- same `dataset_id` and `dataset_version_id`
- same config snapshot
- appending logs, checkpoints, events, restarts, or status changes over time

New `run_id`:

- new training execution attempt
- changed dataset version
- changed training config
- changed base model or parent model version
- changed research intent
- rerun created for comparison

## Checkpoint Rule

Checkpoint files are created by the researcher's training job outside this app. The platform stores only checkpoint metadata:

```text
checkpoint_id
run_id
dataset_version_id
step
checkpoint_uri
metrics_snapshot
created_at
```

A checkpoint can later be promoted to a `model_version`. Promotion is a metadata action in this platform; it links:

```text
dataset_version -> run -> checkpoint -> model_version
```

## Demo Data Source Labels

- Run configs and training metrics: `GENERATED_REAL`, produced by a local lightweight demo trainer that emits raw metric events.
- Compute metrics: realistic demo telemetry derived from the run timeline, bounded by plausible GPU utilization and memory constraints.
- Dataset inputs: public dataset versions already registered in the dataset catalog.
