# Dataset Versioning Rules

Status: **Dataset Agent working rule**

This rule is intentionally strict because dataset versions are part of the
research lineage contract. A training run, checkpoint, model version, eval run,
or failure case must be able to point back to the exact dataset snapshot that
produced it.

## Identifier Meanings

- `dataset_id` is the human-facing catalog identity for a dataset family. In the UI this is shown as a small stable number, such as `1` or `2`.
- `dataset_id` is also the route identity. A dataset detail URL should be `/datasets/{dataset_id}`, such as `/datasets/1`.
- `dataset_name` is the human-readable name, such as `Anthropic HH-RLHF`.
- Public/raw source names remain provenance metadata only. They are not the application identity.
- `dataset_version_id` is the human-facing immutable snapshot number for a dataset, such as `1`.
- `record_id` is the human-facing row number within the displayed dataset version.
- Internal file/storage keys may exist in the storage layer, but they should not be exposed in normal UI or API payloads.

## Dataset Version vs Experiment Variant

Do not use `dataset_version_id` as a synonym for an experiment arm.

- `experiment_variant` means the research condition being tested, such as
  `control`, `outline_first`, or `failure_corrections`.
- `dataset_version_id` means the exact published data snapshot used by a run,
  eval, model, or experiment variant.
- A variant can reference one dataset version or a mixture of multiple dataset
  versions.
- The same dataset version can be reused by many experiments, variants, runs,
  and models.

Correct shape:

```json
{
  "variant_id": 2,
  "variant_name": "outline_first",
  "linked_datasets": [
    { "dataset_id": 7, "dataset_version_id": 1 }
  ]
}
```

For mixtures:

```json
{
  "variant_id": 3,
  "variant_name": "outline_first_plus_failure_replay",
  "data_mixture": [
    { "dataset_id": 1, "dataset_version_id": 1, "weight": 0.8 },
    { "dataset_id": 8, "dataset_version_id": 1, "weight": 0.2 }
  ]
}
```

## When Version Changes

Draft/staging versions can be appended, overwritten, or deleted before publish.
Once a dataset version is published or used by a run, it is immutable.

Keep the same draft/staging `dataset_version_id` when:

- Appending records to the same dataset under the same source, schema, normalizer, and split rules.
- Retrying or resuming ingestion for the same intended snapshot.
- Recomputing display-only metadata that does not affect records, schema, filters, or downstream use.

Create a new `dataset_version_id` when:

- The normalized schema changes.
- Normalization logic changes.
- Filtering, cleaning, dedupe, or PII handling rules change.
- Split assignment or split seed changes.
- Source config/split/source files change in a way that changes dataset meaning.
- A transform stage creates a new asset, such as raw -> normalized -> cleaned -> filtered -> split.
- A published version needs new records appended, overwritten, deleted, or filtered.
- An experiment variant needs a different data snapshot than another variant.

## Local Draft Lifecycle

Before adding cloud storage or signed URL support, the local API uses the same
product lifecycle with local files:

```text
create draft -> append/overwrite records -> validate -> publish
```

The current local endpoints are:

```text
POST /datasets/{dataset_id}/versions/draft
POST /datasets/{dataset_id}/versions/{draft_id}/append
POST /datasets/{dataset_id}/versions/{draft_id}/overwrite
POST /datasets/{dataset_id}/versions/{draft_id}/validate
POST /datasets/{dataset_id}/versions/{draft_id}/publish
GET  /dataset-ingestion-jobs/{job_id}
```

Draft IDs identify mutable staging workspaces only. Publishing allocates the
next immutable public `dataset_version_id` and writes through the same raw,
Parquet, DuckDB, manifest, quality, schema, and lineage path as registered
dataset versions. Cloud object URIs, signed URLs, and researcher authorization
are later phases.

## Current Experiment 1 Mapping

Experiment 1 has three variants. Each variant currently uses a different
published dataset snapshot:

```text
variant_id=1 control
  -> dataset_id=6, dataset_version_id=1

variant_id=2 outline_first
  -> dataset_id=7, dataset_version_id=1

variant_id=3 outline_first_with_failure_corrections
  -> dataset_id=8, dataset_version_id=1
```

Each variant points to a different logical dataset asset, and each asset starts
with its own immutable `dataset_version_id=1`. The dataset version IDs do not
define the variants; the experiment variant records define the variants and
reference the dataset snapshots they use.

Future runs should always carry:

```text
program_id
experiment_id
variant_id
dataset_id
dataset_version_id
```

`variant_id` explains which research arm the run belongs to. `dataset_id` and
`dataset_version_id` explain exactly which governed data snapshot the run used.

## Provenance Requirements

Every dataset detail page should expose:

- Dataset name.
- Human-facing `dataset_id`.
- Human-facing `dataset_version_id`.
- Registration date.
- Last updated date.
- Dataset description.
- Data purpose.
- Data format.
- Public source link.
- Source label: `PUBLIC_REAL`, `GENERATED_REAL`, or `SYNTHETIC_REALISTIC`.
- Numeric `record_id` values for sample records.

## Lineage Display

Lineage should use human-facing IDs first:

```text
dataset_id: 2
source_dataset_version_id: public source
target_dataset_version_id: 1
```

Internal storage keys stay inside the repository/storage layer.

## Record Display

Sample records should show:

```text
record_id: 1
```

The internal record key should stay hidden from normal UI and API responses.
