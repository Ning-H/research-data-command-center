# Dataset Quality Rules

Status: **Dataset Agent working rule**

## What `passed` Means

`quality_status = passed` means the dataset version passed the MVP quality gate:

- Every field required for the dataset's `data_purpose` is populated.
- No required input/target pair is empty after normalization.
- Quality metrics were generated from the normalized Parquet records, not manually invented.

`passed` does **not** mean the dataset is perfect. It means the version is usable for the current research purpose and has no blocking required-field issue.

## Null Value Policy

Nulls are part of quality, but they must be interpreted by dataset purpose.

For example, an instruction-tuning dataset may have empty `chosen_text` and `rejected_text` because those fields only apply to preference data. Those nulls are still profiled in `dataset_schema_profiles`, but they do not fail the gate.

Required fields by purpose:

```text
instruction_tuning -> input_text, target_text
preference_pair -> input_text, chosen_text, rejected_text
summarization -> input_text, target_text
question_answering -> context, question, target_text
coding_eval -> input_text, target_text
```

## Quality Procedure

The MVP follows custom expectation-style checks inspired by Great Expectations, Soda, dbt tests, and data contract validation:

1. Normalize raw public source records into the shared `dataset_records` schema.
2. Profile every normalized field for non-null, null, empty, distinct, and length statistics.
3. Apply purpose-specific required-field checks.
4. Detect exact duplicates with `content_hash`.
5. Compute rough token statistics for input and target text.
6. Run the safe regex PII scanner on fake/test patterns only.
7. Set `quality_status` from required-field failures for the MVP.

## Metrics Currently Exposed

```text
records.total
records.empty_required_field_count
records.duplicate_exact_count
tokens.mean
tokens.p95
pii.fake_test_match_count
quality.gate_status_numeric
schema.null_values.total
```

`schema.null_values.total` is derived from the schema profile in the API response so the detail page can show null quality coverage even before a richer external quality framework is integrated.
