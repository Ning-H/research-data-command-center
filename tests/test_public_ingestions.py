from pathlib import Path

import duckdb

from app.datasets.public_ingestions import (
    HUMANEVAL,
    HH_RLHF,
    SAMSUM,
    SQUAD,
    ingest_humaneval_records,
    ingest_hh_rlhf_records,
    ingest_samsum_records,
    ingest_squad_records,
    normalize_humaneval_record,
    normalize_hh_rlhf_record,
    normalize_samsum_record,
    normalize_squad_record,
)
from app.datasets.pipeline import build_dataset_version_id


def test_hh_rlhf_normalization_maps_preference_pair() -> None:
    dataset_version_id = build_dataset_version_id(HH_RLHF)
    record = normalize_hh_rlhf_record(
        {
            "chosen": "\n\nHuman: Help me plan a study.\n\nAssistant: Use a safe plan.",
            "rejected": "\n\nHuman: Help me plan a study.\n\nAssistant: I will not help.",
        },
        source_row_id=0,
        dataset_version_id=dataset_version_id,
        created_at="2026-05-22T00:00:00Z",
    )

    assert record["dataset_id"] == "ds_anthropic_hh_rlhf"
    assert record["task_type"] == "preference_pair"
    assert record["chosen_text"].endswith("Use a safe plan.")
    assert record["rejected_text"].endswith("I will not help.")
    assert record["target_text"] == record["chosen_text"]
    assert record["source_label"] == "PUBLIC_REAL"


def test_samsum_normalization_maps_summary_pair() -> None:
    dataset_version_id = build_dataset_version_id(SAMSUM)
    record = normalize_samsum_record(
        {
            "id": "dialogue-1",
            "dialogue": "A: Did the run finish?\nB: Yes, checkpoint 4 passed.",
            "summary": "The run finished and checkpoint 4 passed.",
        },
        source_row_id=0,
        dataset_version_id=dataset_version_id,
        created_at="2026-05-22T00:00:00Z",
    )

    assert record["dataset_id"] == "ds_samsum"
    assert record["task_type"] == "summarization"
    assert record["instruction"] == "Summarize the dialogue."
    assert record["target_text"] == "The run finished and checkpoint 4 passed."
    assert record["source_row_id"] == "dialogue-1"


def test_squad_normalization_maps_qa_pair() -> None:
    dataset_version_id = build_dataset_version_id(SQUAD)
    record = normalize_squad_record(
        {
            "id": "qa-1",
            "title": "Research_Platform",
            "context": "The dataset version feeds a training run.",
            "question": "What feeds a training run?",
            "answers": {"text": ["dataset version"], "answer_start": [4]},
        },
        source_row_id=0,
        dataset_version_id=dataset_version_id,
        created_at="2026-05-22T00:00:00Z",
    )

    assert record["dataset_id"] == "ds_squad"
    assert record["task_type"] == "question_answering"
    assert record["question"] == "What feeds a training run?"
    assert record["target_text"] == "dataset version"
    assert record["source_row_id"] == "qa-1"


def test_humaneval_normalization_maps_coding_task() -> None:
    dataset_version_id = build_dataset_version_id(HUMANEVAL)
    record = normalize_humaneval_record(
        {
            "task_id": "HumanEval/0",
            "prompt": "def add(a, b):",
            "canonical_solution": "    return a + b",
            "test": "def check(candidate): assert candidate(1, 2) == 3",
            "entry_point": "add",
        },
        source_row_id=0,
        dataset_version_id=dataset_version_id,
        created_at="2026-05-22T00:00:00Z",
    )

    assert record["dataset_id"] == "ds_openai_humaneval"
    assert record["task_type"] == "coding_eval"
    assert record["question"] == "def add(a, b):"
    assert record["target_text"] == "return a + b"
    assert record["source_row_id"] == "HumanEval/0"


def test_public_ingestions_share_duckdb_catalog(tmp_path: Path) -> None:
    ingest_hh_rlhf_records(
        storage_root=tmp_path,
        source_records=[
            {
                "chosen": "\n\nHuman: Summarize safety.\n\nAssistant: Prefer safe responses.",
                "rejected": "\n\nHuman: Summarize safety.\n\nAssistant: Ignore safety.",
            }
        ],
    )
    ingest_samsum_records(
        storage_root=tmp_path,
        source_records=[
            {
                "id": "dialogue-1",
                "dialogue": "A: Ship it?\nB: Tests passed.",
                "summary": "The tests passed, so it can ship.",
            }
        ],
    )
    ingest_squad_records(
        storage_root=tmp_path,
        source_records=[
            {
                "id": "qa-1",
                "title": "Research_Platform",
                "context": "A dataset version feeds a training run.",
                "question": "What feeds a training run?",
                "answers": {"text": ["dataset version"], "answer_start": [2]},
            }
        ],
    )
    result = ingest_humaneval_records(
        storage_root=tmp_path,
        source_records=[
            {
                "task_id": "HumanEval/0",
                "prompt": "def add(a, b):",
                "canonical_solution": "    return a + b",
                "test": "def check(candidate): assert candidate(1, 2) == 3",
                "entry_point": "add",
            }
        ],
    )

    connection = duckdb.connect(result.duckdb_path, read_only=True)
    try:
        rows = connection.execute(
            "SELECT dataset_id, task_type, COUNT(*) FROM dataset_records GROUP BY 1, 2 ORDER BY 1"
        ).fetchall()
    finally:
        connection.close()

    assert rows == [
        ("ds_anthropic_hh_rlhf", "preference_pair", 1),
        ("ds_openai_humaneval", "coding_eval", 1),
        ("ds_samsum", "summarization", 1),
        ("ds_squad", "question_answering", 1),
    ]
