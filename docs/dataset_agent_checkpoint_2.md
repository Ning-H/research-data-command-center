# Dataset Agent Checkpoint 2: Data Model and Storage Plan

Status: **owner review required before Dataset Agent implementation**

This checkpoint turns the approved Dataset Checkpoint 1 direction into a concrete storage and schema plan. It proposes contract amendments, but does not implement them until approved.

## What The Dataset Agent Plans To Do Next

Create the dataset storage foundation for:

```text
PUBLIC_REAL source records
-> raw landing folders
-> normalized Parquet records
-> metadata rows in Postgres
-> GENERATED_REAL profiles, quality reports, token stats, duplicate reports, and lineage
-> DuckDB views for API/UI queries
```

The first walking skeleton should ingest one compact dataset, normalize it, write version metadata, compute a small quality report, and expose the records through DuckDB.

## Storage Layout

Use local object-store-style folders under `storage/`:

```text
storage/
├── raw/datasets/{dataset_id}/{source_dataset_name}/{ingest_date}/
├── object_store/datasets/{dataset_id}/versions/{dataset_version_id}/
│   ├── manifest.json
│   ├── source_schema.json
│   ├── normalization_report.json
│   └── quality_summary.json
├── parquet/dataset_records/dataset_id={dataset_id}/dataset_version_id={dataset_version_id}/split={split}/records.parquet
├── parquet/dataset_schema_profiles/dataset_id={dataset_id}/dataset_version_id={dataset_version_id}/profile.parquet
├── parquet/dataset_quality_reports/dataset_id={dataset_id}/dataset_version_id={dataset_version_id}/report.parquet
├── parquet/dataset_duplicate_reports/dataset_id={dataset_id}/dataset_version_id={dataset_version_id}/duplicates.parquet
├── parquet/dataset_pii_scan_results/dataset_id={dataset_id}/dataset_version_id={dataset_version_id}/pii.parquet
├── parquet/dataset_token_statistics/dataset_id={dataset_id}/dataset_version_id={dataset_version_id}/tokens.parquet
├── parquet/dataset_lineage/dataset_id={dataset_id}/lineage.parquet
└── duckdb/research_command_center.duckdb
```

Rules:

- Raw data keeps source shape and source filenames where possible.
- Normalized records are Parquet and partitioned by `dataset_id`, `dataset_version_id`, and `split`.
- Postgres stores metadata and URIs only, not bulk record text.
- DuckDB reads Parquet directly and serves analytical/API queries.

## Proposed Metadata Tables In Postgres

### Existing shared table to extend later: `dataset_versions`

Current shared columns are sufficient for the first skeleton:

```text
dataset_id
dataset_version_id
name
version
status
source_priority
raw_uri
parquet_uri
schema_uri
parent_dataset_version_id
created_at
created_by_user_id
```

Recommended later additions after the first skeleton:

```text
description
task_type
source_dataset_name
source_split
record_count
quality_status
quality_report_uri
lineage_uri
```

### New table: `datasets`

Purpose: catalog-level identity across immutable versions.

```text
dataset_id
name
description
category
default_task_type
source_label
owner_user_id
created_at
updated_at
```

### New table: `dataset_ingestion_jobs`

Purpose: track ingestion runs without mixing operational state into immutable dataset versions.

```text
dataset_ingestion_job_id
dataset_id
source_dataset_name
source_config_json
status
started_at
ended_at
records_seen
records_written
error_message
created_by_user_id
```

These two tables are Dataset-Agent-owned and do not affect Runs or Models/Evals directly.

## Proposed Analytical Tables In Parquet + DuckDB

### `dataset_records`

Normalized long-form records:

```text
record_id
dataset_id
dataset_version_id
source_dataset_name
source_split
source_row_id
category
task_type
input_text
instruction
context
question
chosen_text
rejected_text
target_text
response_text
prompt_messages_json
metadata_json
content_hash
source_label
created_at
```

### `dataset_schema_profiles`

One row per field profile:

```text
dataset_version_id
field_name
field_type
non_null_count
null_count
empty_count
distinct_count
min_length
max_length
mean_length
example_values_json
created_at
```

### `dataset_quality_reports`

Keep the shared long-format metric style:

```text
dataset_version_id
timestamp
metric_name
metric_value
source_priority
```

Use metric names such as:

```text
records.total
records.empty_required_field_count
records.duplicate_exact_count
tokens.mean
tokens.p95
pii.fake_test_match_count
quality.gate_status_numeric
```

### `dataset_duplicate_reports`

```text
dataset_version_id
content_hash
duplicate_count
record_ids_json
created_at
```

### `dataset_pii_scan_results`

Safe scanner outputs only. PII examples must be fake/test patterns.

```text
dataset_version_id
record_id
pii_type
match_count
scanner_name
scanner_version
created_at
```

### `dataset_token_statistics`

```text
dataset_version_id
record_id
tokenizer_name
input_token_count
target_token_count
total_token_count
created_at
```

### `dataset_lineage`

Dataset-version edges:

```text
dataset_id
source_dataset_version_id
target_dataset_version_id
lineage_event_type
transform_name
transform_config_uri
created_at
created_by_user_id
```

Allowed `lineage_event_type` values for MVP:

```text
raw_to_normalized
normalized_to_cleaned
cleaned_to_filtered
filtered_to_split
failure_to_candidate
candidate_to_version
```

### Existing shared table: `dataset_usage`

Use when downstream areas exist:

```text
dataset_version_id
run_id
model_version_id
eval_run_id
usage_type
created_at
```

Allowed `usage_type` values for MVP:

```text
training_input
eval_input
model_source
failure_source
dataset_candidate_source
```

## Versioning Rules

- Every dataset version is immutable after `status = published`.
- Any transform creates a new `dataset_version_id`.
- Parent-child edges are stored in `dataset_versions.parent_dataset_version_id` for simple lineage and in `dataset_lineage` for the full graph.
- Version IDs should be deterministic enough for demos but unique:

```text
dsv_{dataset_slug}_{stage}_{yyyymmdd}_{short_hash}
```

- Record IDs should be stable across reruns:

```text
rec_{dataset_version_id}_{source_split}_{source_row_id}_{content_hash_prefix}
```

## First Walking Skeleton

Use `databricks/databricks-dolly-15k` first because it is compact and training-data oriented.

Implement the thinnest end-to-end path:

```text
download/load source
-> raw manifest
-> normalize to dataset_records Parquet
-> create datasets + dataset_versions metadata
-> compute schema profile
-> compute basic quality report
-> create raw_to_normalized lineage edge
-> create DuckDB views over the Parquet outputs
```

Then add `Anthropic/hh-rlhf` as the second dataset because it validates chosen/rejected preference schema.

## Contract Amendments Requested

Add Dataset-Agent-owned tables to the shared contract after approval:

- `datasets` in Postgres.
- `dataset_ingestion_jobs` in Postgres.
- `dataset_records` in Parquet + DuckDB.
- `dataset_schema_profiles` in Parquet + DuckDB.
- `dataset_duplicate_reports` in Parquet + DuckDB.
- `dataset_pii_scan_results` in Parquet + DuckDB.
- `dataset_token_statistics` in Parquet + DuckDB.
- `dataset_lineage` in Parquet + DuckDB.

No new canonical cross-agent identifiers are requested.

## Open Questions / Assumptions

- Keep `source_priority` as the column name for compatibility with the existing contract, but values must be `PUBLIC_REAL`, `GENERATED_REAL`, or `SYNTHETIC_REALISTIC`.
- Use Postgres for metadata in the contract, but allow a local development fallback later only if setup friction blocks demos.
- Do not build arbitrary file upload/registration until the public dataset ingestion skeleton works.
- Do not implement fuzzy duplicate detection in MVP; exact duplicates first.

## Explicit Ask

Confirm to proceed with these dataset storage/table amendments and the Dolly-first walking skeleton, or adjust the storage/model plan before implementation.
