from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from research_command_center_contract.enums import SourcePriority

from app.datasets.pipeline import (
    DatasetDefinition,
    IngestionResult,
    build_dataset_version_id,
    build_record_id,
    clean_text,
    content_hash_for_fields,
    utc_now_iso,
    write_dataset_outputs,
    write_raw_jsonl,
)

HH_RLHF = DatasetDefinition(
    dataset_id="ds_anthropic_hh_rlhf",
    slug="anthropic_hh_rlhf",
    display_name="Anthropic HH-RLHF",
    source_dataset_name="Anthropic/hh-rlhf",
    category="preference_safety",
    task_type="preference_pair",
    description="Chosen/rejected assistant responses used for preference, helpfulness, and safety research workflows.",
    transform_name="normalize_anthropic_hh_rlhf",
)

SAMSUM = DatasetDefinition(
    dataset_id="ds_samsum",
    slug="samsum",
    display_name="SAMSum Dialogue Summarization",
    source_dataset_name="knkarthick/samsum",
    category="summarization",
    task_type="summarization",
    description="Dialogue-summary pairs used for summarization training and evaluation workflows.",
    transform_name="normalize_samsum",
)

SQUAD = DatasetDefinition(
    dataset_id="ds_squad",
    slug="squad",
    display_name="SQuAD Question Answering",
    source_dataset_name="allenai/squad",
    category="question_answering",
    task_type="question_answering",
    description="Context/question/answer records used for QA evaluation and optional training workflows.",
    transform_name="normalize_squad",
)

HUMANEVAL = DatasetDefinition(
    dataset_id="ds_openai_humaneval",
    slug="openai_humaneval",
    display_name="OpenAI HumanEval",
    source_dataset_name="openai/openai_humaneval",
    category="coding_eval",
    task_type="coding_eval",
    description="Python coding benchmark tasks with prompts, canonical solutions, and tests for evaluation workflows.",
    transform_name="normalize_openai_humaneval",
)

NORMALIZERS: dict[str, tuple[DatasetDefinition, Callable[[dict[str, Any], int, str, str, str], dict[str, Any]]]] = {
    "hh-rlhf": (HH_RLHF, lambda row, row_id, version_id, created_at, split: normalize_hh_rlhf_record(row, row_id, version_id, created_at, split)),
    "humaneval": (HUMANEVAL, lambda row, row_id, version_id, created_at, split: normalize_humaneval_record(row, row_id, version_id, created_at, split)),
    "samsum": (SAMSUM, lambda row, row_id, version_id, created_at, split: normalize_samsum_record(row, row_id, version_id, created_at, split)),
    "squad": (SQUAD, lambda row, row_id, version_id, created_at, split: normalize_squad_record(row, row_id, version_id, created_at, split)),
}

DEFAULT_CONFIGS = {
    "humaneval": "openai_humaneval",
}

DEFAULT_SPLITS = {
    "humaneval": "test",
}


def fetch_hugging_face_rows(
    dataset_name: str,
    split: str = "train",
    config: str = "default",
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    url = "https://datasets-server.huggingface.co/rows?" + urllib.parse.urlencode(
        {
            "dataset": dataset_name,
            "config": config,
            "split": split,
            "offset": offset,
            "length": limit,
        }
    )
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.load(response)
    return [row["row"] for row in payload.get("rows", [])]


def normalize_hh_rlhf_record(
    source_row: dict[str, Any],
    source_row_id: int,
    dataset_version_id: str,
    created_at: str,
    source_split: str = "train",
) -> dict[str, Any]:
    chosen = clean_text(source_row.get("chosen"))
    rejected = clean_text(source_row.get("rejected"))
    prompt = _extract_preference_prompt(chosen, rejected)
    content_hash = content_hash_for_fields(prompt, chosen, rejected)
    return _base_record(
        definition=HH_RLHF,
        dataset_version_id=dataset_version_id,
        source_split=source_split,
        source_row_id=source_row_id,
        category="preference_safety",
        input_text=prompt,
        instruction="Compare assistant responses for helpfulness and safety.",
        context=prompt,
        question="",
        chosen_text=chosen,
        rejected_text=rejected,
        target_text=chosen,
        response_text=chosen,
        metadata={"preference_source": "hh_rlhf"},
        content_hash=content_hash,
        created_at=created_at,
    )


def normalize_samsum_record(
    source_row: dict[str, Any],
    source_row_id: int,
    dataset_version_id: str,
    created_at: str,
    source_split: str = "train",
) -> dict[str, Any]:
    dialogue = clean_text(source_row.get("dialogue"))
    summary = clean_text(source_row.get("summary"))
    source_id = clean_text(source_row.get("id")) or str(source_row_id)
    content_hash = content_hash_for_fields(dialogue, summary, source_id)
    return _base_record(
        definition=SAMSUM,
        dataset_version_id=dataset_version_id,
        source_split=source_split,
        source_row_id=source_id,
        category="summarization",
        input_text=dialogue,
        instruction="Summarize the dialogue.",
        context=dialogue,
        question="",
        chosen_text="",
        rejected_text="",
        target_text=summary,
        response_text=summary,
        metadata={"source_id": source_id},
        content_hash=content_hash,
        created_at=created_at,
    )


def normalize_squad_record(
    source_row: dict[str, Any],
    source_row_id: int,
    dataset_version_id: str,
    created_at: str,
    source_split: str = "train",
) -> dict[str, Any]:
    source_id = clean_text(source_row.get("id")) or str(source_row_id)
    title = clean_text(source_row.get("title"))
    context = clean_text(source_row.get("context"))
    question = clean_text(source_row.get("question"))
    answers = source_row.get("answers") or {}
    answer_texts = answers.get("text") or []
    target_text = clean_text(answer_texts[0] if answer_texts else "")
    input_text = f"{context}\n\nQuestion: {question}".strip()
    content_hash = content_hash_for_fields(source_id, context, question, target_text)
    return _base_record(
        definition=SQUAD,
        dataset_version_id=dataset_version_id,
        source_split=source_split,
        source_row_id=source_id,
        category="question_answering",
        input_text=input_text,
        instruction="Answer the question using the provided context.",
        context=context,
        question=question,
        chosen_text="",
        rejected_text="",
        target_text=target_text,
        response_text=target_text,
        metadata={"title": title, "answers": answers},
        content_hash=content_hash,
        created_at=created_at,
    )


def normalize_humaneval_record(
    source_row: dict[str, Any],
    source_row_id: int,
    dataset_version_id: str,
    created_at: str,
    source_split: str = "test",
) -> dict[str, Any]:
    task_id = clean_text(source_row.get("task_id")) or str(source_row_id)
    prompt = clean_text(source_row.get("prompt"))
    canonical_solution = clean_text(source_row.get("canonical_solution"))
    test_code = clean_text(source_row.get("test"))
    entry_point = clean_text(source_row.get("entry_point"))
    content_hash = content_hash_for_fields(task_id, prompt, canonical_solution, test_code)
    return _base_record(
        definition=HUMANEVAL,
        dataset_version_id=dataset_version_id,
        source_split=source_split,
        source_row_id=task_id,
        category="coding_eval",
        input_text=prompt,
        instruction="Complete the Python function so it passes the provided tests.",
        context=test_code,
        question=prompt,
        chosen_text="",
        rejected_text="",
        target_text=canonical_solution,
        response_text=canonical_solution,
        metadata={"task_id": task_id, "entry_point": entry_point, "test": test_code},
        content_hash=content_hash,
        created_at=created_at,
    )


def ingest_hh_rlhf_records(
    storage_root: Path,
    source_records: list[dict[str, Any]],
    source_split: str = "train",
) -> IngestionResult:
    return _ingest_records(storage_root, HH_RLHF, source_records, normalize_hh_rlhf_record, source_split)


def ingest_samsum_records(
    storage_root: Path,
    source_records: list[dict[str, Any]],
    source_split: str = "train",
) -> IngestionResult:
    return _ingest_records(storage_root, SAMSUM, source_records, normalize_samsum_record, source_split)


def ingest_squad_records(
    storage_root: Path,
    source_records: list[dict[str, Any]],
    source_split: str = "train",
) -> IngestionResult:
    return _ingest_records(storage_root, SQUAD, source_records, normalize_squad_record, source_split)


def ingest_humaneval_records(
    storage_root: Path,
    source_records: list[dict[str, Any]],
    source_split: str = "test",
) -> IngestionResult:
    return _ingest_records(storage_root, HUMANEVAL, source_records, normalize_humaneval_record, source_split)


def ingest_from_hugging_face(
    storage_root: Path,
    dataset_key: str,
    split: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> IngestionResult:
    definition, normalizer = NORMALIZERS[dataset_key]
    resolved_split = split or DEFAULT_SPLITS.get(dataset_key, "train")
    source_records = fetch_hugging_face_rows(
        dataset_name=definition.source_dataset_name,
        config=DEFAULT_CONFIGS.get(dataset_key, "default"),
        split=resolved_split,
        limit=limit,
        offset=offset,
    )
    return _ingest_records(storage_root, definition, source_records, normalizer, resolved_split)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest sampled public Hugging Face datasets.")
    parser.add_argument("dataset", choices=sorted(NORMALIZERS.keys()))
    parser.add_argument("--storage-root", default="storage", type=Path)
    parser.add_argument("--split", default=None)
    parser.add_argument("--limit", default=100, type=int)
    parser.add_argument("--offset", default=0, type=int)
    args = parser.parse_args(argv)

    result = ingest_from_hugging_face(
        storage_root=args.storage_root,
        dataset_key=args.dataset,
        split=args.split,
        limit=args.limit,
        offset=args.offset,
    )
    print(json.dumps(result.__dict__, indent=2, sort_keys=True))
    return 0


def _ingest_records(
    storage_root: Path,
    definition: DatasetDefinition,
    source_records: list[dict[str, Any]],
    normalizer: Callable[[dict[str, Any], int, str, str, str], dict[str, Any]],
    source_split: str,
) -> IngestionResult:
    created_at = utc_now_iso()
    dataset_version_id = build_dataset_version_id(definition)
    raw_path = (
        storage_root
        / "raw"
        / "datasets"
        / definition.dataset_id
        / definition.slug
        / created_at[:10]
        / f"{source_split}.jsonl"
    )
    write_raw_jsonl(source_records, raw_path)
    normalized_records = [
        normalizer(record, index, dataset_version_id, created_at, source_split)
        for index, record in enumerate(source_records)
    ]
    return write_dataset_outputs(
        storage_root=storage_root,
        definition=definition,
        source_records=source_records,
        normalized_records=normalized_records,
        raw_path=raw_path,
        dataset_version_id=dataset_version_id,
        created_at=created_at,
    )


def _base_record(
    definition: DatasetDefinition,
    dataset_version_id: str,
    source_split: str,
    source_row_id: int | str,
    category: str,
    input_text: str,
    instruction: str,
    context: str,
    question: str,
    chosen_text: str,
    rejected_text: str,
    target_text: str,
    response_text: str,
    metadata: dict[str, Any],
    content_hash: str,
    created_at: str,
) -> dict[str, Any]:
    return {
        "record_id": build_record_id(dataset_version_id, source_split, str(source_row_id), content_hash),
        "dataset_id": definition.dataset_id,
        "dataset_version_id": dataset_version_id,
        "source_dataset_name": definition.source_dataset_name,
        "source_split": source_split,
        "source_row_id": str(source_row_id),
        "category": category,
        "task_type": definition.task_type,
        "input_text": input_text,
        "instruction": instruction,
        "context": context,
        "question": question,
        "chosen_text": chosen_text,
        "rejected_text": rejected_text,
        "target_text": target_text,
        "response_text": response_text,
        "prompt_messages_json": json.dumps([{"role": "user", "content": input_text}], ensure_ascii=True),
        "metadata_json": json.dumps(metadata, ensure_ascii=True),
        "content_hash": content_hash,
        "source_label": SourcePriority.PUBLIC_REAL.value,
        "created_at": created_at,
    }


def _extract_preference_prompt(chosen: str, rejected: str) -> str:
    shared_length = 0
    for chosen_char, rejected_char in zip(chosen, rejected, strict=False):
        if chosen_char != rejected_char:
            break
        shared_length += 1
    prompt = chosen[:shared_length].rsplit("\n\nAssistant:", 1)[0]
    return prompt.strip() or "Preference comparison conversation"


if __name__ == "__main__":
    raise SystemExit(main())
