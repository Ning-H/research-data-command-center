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
