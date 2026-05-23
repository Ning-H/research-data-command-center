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

The preferred real local trainer for this project is:

```text
scripts/train_registered_torch_classifier.py
```

It behaves like a researcher's external training job:

- reads registered dataset records through the API using `dataset_id` and `dataset_version_id`
- registers a new run through `POST /runs/register`
- trains a small PyTorch text classifier outside the application
- writes TensorBoard scalar logs for loss, accuracy, throughput, memory, and cost
- appends real loss, accuracy, token-throughput, CPU time, memory, and cost metrics
- writes real local `.pt` checkpoint artifacts
- appends checkpoint metadata through `POST /runs/{run_id}/checkpoints`
- completes the run through `POST /runs/{run_id}/complete`

Local PyTorch setup note:

```text
arch -arm64 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m venv .venv-arm64-torch
arch -arm64 .venv-arm64-torch/bin/python -m pip install -e . torch tensorboard
arch -arm64 .venv-arm64-torch/bin/python scripts/train_registered_torch_classifier.py
```

The separate arm64 environment is needed on the owner's current machine because
the installed `uv` binary is x86_64 while PyTorch's Python 3.13 macOS wheel is
available for arm64.

The older `scripts/train_registered_text_classifier.py` NumPy trainer remains as
a lightweight fallback, but PyTorch + TensorBoard is the portfolio-facing
training path.

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

Every `checkpoint_id` belongs to exactly one `run_id`. This is required because
the run carries the dataset, config, base model, trainer, owner, and execution
context needed to interpret the checkpoint.

The checkpoint metadata is stored as a separate analytical table so researchers
can search and rank checkpoints across runs:

```text
GET /checkpoints?dataset_id=1&dataset_version_id=1&framework=pytorch&trainer=train_registered_torch_classifier&ranking_metric=train.accuracy&direction=desc
```

The actual artifact file may stay under a run-owned object-store path:

```text
storage/object_store/training_jobs/run_id=7/torch_checkpoint_epoch_8_step_56.pt
```

That layout is acceptable because the checkpoint file was produced by that run.
Cross-run discovery must use the checkpoint metadata table, not filesystem
walking.

A checkpoint can later be promoted to a `model_version`. Promotion is a metadata action in this platform; it links:

```text
dataset_version -> run -> checkpoint -> model_version
```

## Demo Data Source Labels

- Runs created by `scripts/train_registered_torch_classifier.py`: `GENERATED_REAL`.
- Runs created by `scripts/train_registered_text_classifier.py`: `GENERATED_REAL`, lightweight fallback.
- Temporary rows created by `scripts/seed_demo_runs.py`: `SYNTHETIC_REALISTIC`.
- MLflow/W&B/TensorBoard imports, when added later, should preserve their original raw event files and map scalars/system metrics into the same long-format metric tables.
- Dataset inputs: public dataset versions already registered in the dataset catalog.

## Cost Rule

`cost.estimated_usd` is not inferred from model tokens. It comes from the execution
environment:

```text
runtime_hours * hourly_compute_rate_usd
```

For local development on the owner's machine, the default hourly rate is `0.0`,
because there is no cloud bill. For cloud GPU jobs, the trainer or import adapter
must submit the instance/GPU hourly rate used for the run.

## Experiment Tracker Integration Rule

W&B, MLflow, and TensorBoard are optional input sources, not the source of truth
for v1. The platform source of truth is still:

```text
registered dataset -> registered run_id -> raw events -> normalized metrics/checkpoints
```

Tracker integrations should work as import/mirroring adapters:

- W&B can provide training metrics and system metrics, including Apple ARM Mac GPU metrics when the W&B SDK is used.
- MLflow can provide metrics, artifacts, and system metrics; system metrics require `psutil`, and NVIDIA GPU metrics require `nvidia-ml-py`.
- TensorBoard can provide scalar event logs that can be loaded into tabular form and normalized into `training_metrics`.
