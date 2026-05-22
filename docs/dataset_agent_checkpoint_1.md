# Dataset Agent Checkpoint 1: Data Source Plan

Status: **owner review required before Dataset Agent implementation**

This checkpoint follows `docs/ai_agent_build_guidelines.md` and consumes the shared contract in `docs/shared_data_contract.md`.

## What The Dataset Agent Plans To Do Next

Build the first dataset vertical slice around real public datasets:

```text
Public dataset source
-> raw local object-store copy or streaming reference
-> normalized Parquet records
-> dataset version metadata
-> schema profile
-> quality report
-> catalog/detail API and UI later
```

The first implementation phase should ingest and normalize a small, representative sample per dataset category before expanding volume.

## Proposed Public Datasets

| Category | Dataset | Label | Why It Fits MVP | Initial Size |
|---|---|---:|---|---:|
| Instruction / QA-style instruction | `databricks/databricks-dolly-15k` | `PUBLIC_REAL` | Human-written instruction-following records with categories and compact enough for full local ingestion. | Full 15k |
| Preference / safety / helpfulness | `Anthropic/hh-rlhf` | `PUBLIC_REAL` | Chosen/rejected preference pairs are ideal for versioning, quality checks, and later eval/failure workflows. | Sample 10k-25k first |
| Summarization | `knkarthick/samsum` | `PUBLIC_REAL` | Dialogue-summary pairs make schema normalization visibly different from instruction/preference data. | Full about 16k |
| QA | `allenai/squad` | `PUBLIC_REAL` | Classic context/question/answer format; useful for records explorer and eval handoff. | Sample 10k first |
| Coding / eval cases | `openai/openai_humaneval` | `PUBLIC_REAL` | Small coding benchmark useful for cataloging eval-style data and later Models/Evals integration. | Full dataset |

Optional later dataset:

- `tatsu-lab/alpaca`: useful as a large instruction schema stress test, but because it is model-generated, it should not be the first quality anchor.

## Generated And Synthetic Data Boundaries

`GENERATED_REAL`:

- Schema profiles computed from ingested records.
- Dataset quality reports.
- Token statistics.
- Duplicate reports.
- Split summaries.
- Dataset lineage records for raw -> normalized -> cleaned -> filtered -> split.
- Dataset usage records once Runs and Models/Evals exist.

`SYNTHETIC_REALISTIC`:

- Dataset owner/team names.
- Review notes.
- Approval decisions.
- Sensitivity labels.
- Quality-gate decisions.
- Fake/test PII examples used only to validate the scanner.

The Dataset Agent must not synthesize core dataset records for MVP because public datasets are available.

## Initial Internal Record Schema

Normalize heterogeneous source datasets into a common long-form record table stored as Parquet:

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

Notes:

- `dataset_id` and `dataset_version_id` must use the shared canonical keys.
- Source-specific fields that do not fit the common schema go into `metadata_json`.
- `content_hash` supports exact duplicate detection and immutable versioning.
- Large text records stay in Parquet/object storage, not Postgres.

## Quality Check Suite

First quality suite:

- Schema completeness by dataset and split.
- Required-field null/empty checks by `task_type`.
- Record count by split/category.
- Text length and approximate token statistics.
- Exact duplicate detection using `content_hash`.
- Near-duplicate placeholder metric for later fuzzy hashing.
- Safe PII scan using regex and fake/test examples only.
- Basic unsafe-content flag counts for HH-RLHF metadata visibility, without treating it as a moderation product.
- Quality gate summary: `passed`, `warning`, or `failed`.

## Versioning And Lineage Model

Dataset version stages:

```text
raw_dataset_version
-> normalized_dataset_version
-> cleaned_dataset_version
-> filtered_dataset_version
-> train/eval split dataset_version
```

Each version must store:

- `dataset_id`
- `dataset_version_id`
- parent version id where applicable
- source dataset name and source label
- raw URI
- Parquet URI
- schema/profile URI
- quality report URI
- immutable creation timestamp

Lineage should answer:

- Which public source produced this version?
- What transform created it?
- Which parent version did it come from?
- Which future runs, models, and evals used it?

## Open Questions / Assumptions

- MVP starts with Datasets first, then Runs, then Models/Evals.
- Postgres stores metadata only; records and quality outputs are stored as Parquet plus DuckDB views.
- Initial ingestion should prefer samples for large datasets and full ingestion for compact datasets.
- Dataset registration from arbitrary user files is designed in Dataset Checkpoint 3, after the public-source path works.

## Explicit Ask

Confirm to proceed with Dataset Checkpoint 2: Data Model and Storage Plan, or adjust the dataset choices/initial sizes first.

## Source References

- `databricks/databricks-dolly-15k`: https://huggingface.co/datasets/databricks/databricks-dolly-15k
- `Anthropic/hh-rlhf`: https://huggingface.co/datasets/Anthropic/hh-rlhf
- `knkarthick/samsum`: https://huggingface.co/datasets/knkarthick/samsum
- `allenai/squad`: https://huggingface.co/datasets/allenai/squad
- `openai/openai_humaneval`: https://huggingface.co/datasets/openai/openai_humaneval
- `tatsu-lab/alpaca`: https://huggingface.co/datasets/tatsu-lab/alpaca
