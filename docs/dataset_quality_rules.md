# Dataset Quality Rules

Status: **Dataset Agent working rule**

## Quality Score

The main quality signal is `quality_score`, a 1-100 score for a dataset version.

Score bands:

```text
90-100 -> Excellent
75-89  -> Good
60-74  -> Needs review
1-59   -> Blocked
```

The score is not a claim that the dataset is perfect. It is a compact signal that summarizes whether the version is usable for the current research purpose, backed by detailed metrics and checks.

## Score Formula

The MVP score uses a weighted, auditable formula:

```text
60 points -> required-field completeness
15 points -> exact duplicate rate
15 points -> safe PII scan match rate
10 points -> generated schema/profile coverage
```

Required-field completeness is weighted highest because a dataset with missing purpose-critical fields cannot safely move into runs or evals.

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
7. Calculate `quality_score` from the weighted checks.

## Metrics Currently Exposed

```text
records.total
records.empty_required_field_count
records.duplicate_exact_count
tokens.mean
tokens.p95
pii.fake_test_match_count
quality.gate_status_numeric
quality.score
schema.null_values.total
```

`quality.score` and `schema.null_values.total` are derived in the API response so the detail page can show a clean score and null quality coverage before a richer external quality framework is integrated.
