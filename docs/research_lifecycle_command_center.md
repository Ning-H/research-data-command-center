# Research Lifecycle Command Center Direction

Status: active product direction

## Problem Statement

AI research teams run many experiments across datasets, training jobs, model
checkpoints, evaluations, inference traces, and failure cases. The work is
often fragmented across notebooks, dashboards, object storage, experiment
trackers, logs, spreadsheets, and internal docs.

Researchers need to answer:

```text
What changed, why did model behavior change, which data/run/checkpoint caused
it, and what should we try next?
```

## Product Goal

Research Data Command Center is a lineage-first research operations platform.
It connects:

```text
Research Program
-> Hypothesis
-> Data Assets
-> Data Mixtures
-> Experiments
-> Training Runs
-> Checkpoints
-> Model Versions
-> Evaluation Runs
-> Inference Traces
-> Failure Cases
-> Dataset Candidates
-> Next Experiment
```

## Navigation

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

## Core Product Questions

Every feature must answer at least one:

- What research goal are we working on?
- What hypothesis are we testing?
- What data was used?
- What changed between runs?
- Which checkpoint/model came from which run?
- How did the model perform?
- Where did it fail?
- What dataset/version should be created next?

## Core Entities

```text
research_programs
hypotheses
data_assets
data_asset_versions
data_mixtures
data_mixture_items
experiments
experiment_variants
training_runs
training_run_metrics
checkpoints
model_versions
eval_suites
eval_tasks
eval_runs
eval_results
inference_traces
tool_calls
failure_cases
dataset_candidates
lineage_edges
```

`lineage_edges` is the future cross-domain graph table. Existing tables still
keep explicit foreign keys because direct joins should remain easy.

Example edge:

```text
source_type = data_asset_version
source_id = 3
target_type = training_run
target_id = 102
relationship = used_by
```

## Demo Flow

```text
1. Research Program:
   Improve tool-use reliability.

2. Hypothesis:
   Adding high-quality tool-use traces improves task success.

3. Data Assets:
   SFT data + tool-use traces + safety examples.

4. Data Mixture:
   70% instruction data, 20% tool-use traces, 10% safety data.

5. Training Run:
   SFT run using that mixture.

6. Model Version:
   model-v0.2 generated from checkpoint-003.

7. Evaluation:
   Tool-use success improves, but safety refusal regression appears.

8. Failure Library:
   Unsafe tool-use failures are captured.

9. Dataset Candidate:
   Convert failures into new safety/tool-use training examples.

10. Next Experiment:
   Run v0.3 with improved safety mixture.
```

## Build Phases

1. Product direction: README, navigation, entity list, API contract draft, mock home.
2. Shared contract + backend skeleton: schemas, routes, seed data, lineage edges.
3. Frontend navigation + home: summary cards, recent activity, alerts.
4. Data assets + data mixtures: registry, version page, quality, public sample datasets.
5. Experiments + training runs: hypothesis -> mixture -> run -> checkpoint.
6. Models + evaluations: registry, lineage, eval suite, comparison, regressions.
7. Inference observability: traces, latency/token/cost summary, tool calls.
8. Failure library + dataset iterations: failure review, root cause, candidate creation.

Stop at human checkpoints before expanding scope or changing shared contracts.
