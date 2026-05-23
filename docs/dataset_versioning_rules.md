# Dataset Versioning Rules

Status: **Dataset Agent working rule**

## Identifier Meanings

- `dataset_id` is the human-facing catalog identity for a dataset family. In the UI this is shown as a small stable number, such as `1` or `2`.
- `dataset_id` is also the route identity. A dataset detail URL should be `/datasets/{dataset_id}`, such as `/datasets/1`.
- `dataset_name` is the human-readable name, such as `Anthropic HH-RLHF`.
- Public/raw source names remain provenance metadata only. They are not the application identity.
- `dataset_version_id` is the human-facing current version number for a dataset, such as `1`.
- `record_id` is the human-facing row number within the displayed dataset version.
- Internal file/storage keys may exist in the storage layer, but they should not be exposed in normal UI or API payloads.

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
