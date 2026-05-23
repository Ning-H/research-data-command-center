# Dataset Versioning Rules

Status: **Dataset Agent working rule**

## Identifier Meanings

- `dataset_id` is the human-facing catalog identity for a dataset family. In the UI this is shown as a small stable number, such as `1` or `2`.
- `dataset_slug` / route key is the URL-safe technical identifier, such as `ds_anthropic_hh_rlhf`.
- `dataset_version_id` is the human-facing current version number for a dataset, such as `1`.
- `dataset_version_storage_key` is the immutable backend storage key, such as `dsv_anthropic_hh_rlhf_raw_v1_7b57e8e5e3`.
- `record_id` is the human-facing row number within the displayed dataset version.
- `record_storage_key` is the deterministic backend record key used for storage and joins.

## When Version Changes

Keep the same `dataset_version_id` when:

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

## Provenance Requirements

Every dataset detail page should expose:

- Dataset name.
- Human-facing `dataset_id`.
- Human-facing `dataset_version_id`.
- Public source link.
- Source label: `PUBLIC_REAL`, `GENERATED_REAL`, or `SYNTHETIC_REALISTIC`.
- Backend route/storage keys in secondary metadata for traceability.

## Lineage Display

Lineage should use human-facing IDs first:

```text
dataset_id: 2
source_dataset_version_id: public source
target_dataset_version_id: 1
```

Backend storage keys can be shown as secondary values only when useful for debugging or API traceability.

## Record Display

Sample records should show:

```text
record_id: 1
```

The deterministic backend record key remains available as `record_storage_key`, but should not be the primary visual identifier.
