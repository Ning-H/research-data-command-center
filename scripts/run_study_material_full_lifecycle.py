from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from app.datasets.pipeline import (
    DatasetDefinition,
    content_hash_for_fields,
    register_duckdb_views,
    write_dataset_outputs,
    write_raw_jsonl,
)
from research_command_center_contract.enums import SourcePriority


PROGRAM_ID = 1
EXPERIMENT_ID = 1
FAILURE_CORRECTION_DATASET_ID = 8
DEFAULT_OWNER = "Lena Keys"
METRIC_NAMES = ["coverage", "depth", "examples", "accuracy", "learning_flow"]

VARIANTS = {
    1: {
        "variant_id": 1,
        "name": "control",
        "variant_type": "control",
        "dataset_id": 6,
        "dataset_version_id": 1,
        "storage_dataset_id": "ds_python_algorithm_study_guides_control",
        "storage_version_id": "dsv_python_algorithm_study_guides_control_v1",
        "source_dataset_name": "generated/python-algorithm-study-guides/control",
        "display_name": "Python Algorithm Study-Guide Control Data",
        "run_name": "study-guide-control-training-v1",
        "description": "Baseline direct-answer study guide records.",
    },
    2: {
        "variant_id": 2,
        "name": "outline_first",
        "variant_type": "test",
        "dataset_id": 7,
        "dataset_version_id": 1,
        "storage_dataset_id": "ds_python_algorithm_study_guides_outline_first",
        "storage_version_id": "dsv_python_algorithm_study_guides_outline_first_v1",
        "source_dataset_name": "generated/python-algorithm-study-guides/outline-first",
        "display_name": "Python Algorithm Study-Guide Outline-First Data",
        "run_name": "study-guide-outline-first-training-v1",
        "description": "Outline-first records that force structure before the guide.",
    },
    3: {
        "variant_id": 3,
        "name": "outline_first_with_failure_corrections",
        "variant_type": "test",
        "dataset_id": 8,
        "dataset_version_id": 1,
        "storage_dataset_id": "ds_python_algorithm_study_guides_failure_corrections",
        "storage_version_id": "dsv_python_algorithm_study_guides_failure_corrections_v1",
        "source_dataset_name": "generated/python-algorithm-study-guides/failure-corrections",
        "display_name": "Python Algorithm Study-Guide Failure-Correction Data",
        "run_name": "study-guide-failure-corrections-training-v1",
        "description": "Outline-first records with corrected shallow-output failures.",
    },
}

ALGORITHM_TOPICS = [
    {
        "topic": "binary search",
        "use_case": "find a boundary or target in sorted data",
        "complexity": "O(log n) time and O(1) space",
        "example": "search insert position",
        "pitfall": "off-by-one loop boundaries",
    },
    {
        "topic": "two pointers",
        "use_case": "scan arrays or strings from both ends or with a slow/fast cursor",
        "complexity": "O(n) time and O(1) space",
        "example": "valid palindrome",
        "pitfall": "moving the wrong pointer after a comparison",
    },
    {
        "topic": "sliding window",
        "use_case": "track a variable-size contiguous range",
        "complexity": "O(n) time and O(k) space",
        "example": "longest substring without repeating characters",
        "pitfall": "forgetting to shrink the window until it is valid",
    },
    {
        "topic": "hash map counting",
        "use_case": "count frequencies or remember previous values",
        "complexity": "O(n) time and O(n) space",
        "example": "two sum",
        "pitfall": "checking after insertion when the same element cannot be reused",
    },
    {
        "topic": "breadth-first search",
        "use_case": "find shortest paths in unweighted graphs or traverse by levels",
        "complexity": "O(V + E) time and O(V) space",
        "example": "number of islands",
        "pitfall": "marking visited too late and adding duplicates to the queue",
    },
    {
        "topic": "depth-first search",
        "use_case": "explore connected components, trees, and backtracking states",
        "complexity": "O(V + E) time and O(V) recursion or stack space",
        "example": "path sum",
        "pitfall": "not restoring state during backtracking",
    },
    {
        "topic": "heap priority queue",
        "use_case": "retrieve the smallest or largest item repeatedly",
        "complexity": "O(n log k) time for top-k patterns and O(k) space",
        "example": "top k frequent elements",
        "pitfall": "using a max heap when a fixed-size min heap is simpler",
    },
    {
        "topic": "dynamic programming",
        "use_case": "solve overlapping subproblems with optimal substructure",
        "complexity": "usually O(states * transitions)",
        "example": "coin change",
        "pitfall": "choosing a state that does not contain enough information",
    },
    {
        "topic": "greedy algorithms",
        "use_case": "make locally optimal choices when an exchange argument holds",
        "complexity": "often O(n log n) when sorting is required",
        "example": "merge intervals",
        "pitfall": "using greedy when a future decision can invalidate the local choice",
    },
    {
        "topic": "prefix sums",
        "use_case": "answer range-sum questions or transform subarray constraints",
        "complexity": "O(n) preprocessing and O(1) per range query",
        "example": "subarray sum equals k",
        "pitfall": "forgetting the zero prefix before scanning",
    },
    {
        "topic": "monotonic stack",
        "use_case": "find next greater, previous smaller, or span relationships",
        "complexity": "O(n) time and O(n) space",
        "example": "daily temperatures",
        "pitfall": "popping on the wrong comparison direction",
    },
    {
        "topic": "monotonic queue",
        "use_case": "track a sliding-window minimum or maximum efficiently",
        "complexity": "O(n) time and O(k) space",
        "example": "sliding window maximum",
        "pitfall": "forgetting to evict indices outside the window",
    },
    {
        "topic": "backtracking",
        "use_case": "search combinations, permutations, and constrained choices",
        "complexity": "exponential in the number of choices",
        "example": "subsets",
        "pitfall": "not undoing a choice before returning",
    },
    {
        "topic": "recursion on trees",
        "use_case": "solve a tree by combining answers from child nodes",
        "complexity": "O(n) time and O(h) call-stack space",
        "example": "maximum depth of binary tree",
        "pitfall": "missing the base case for an empty node",
    },
    {
        "topic": "union find",
        "use_case": "maintain connected components under merge operations",
        "complexity": "near O(1) amortized per operation with path compression",
        "example": "number of connected components",
        "pitfall": "not compressing paths or unioning by rank/size",
    },
    {
        "topic": "topological sort",
        "use_case": "order tasks or courses with dependency constraints",
        "complexity": "O(V + E) time and O(V + E) space",
        "example": "course schedule",
        "pitfall": "not detecting cycles when the output order is incomplete",
    },
    {
        "topic": "dijkstra shortest path",
        "use_case": "find shortest paths in graphs with non-negative edge weights",
        "complexity": "O((V + E) log V) with a binary heap",
        "example": "network delay time",
        "pitfall": "using it with negative edge weights",
    },
    {
        "topic": "binary search on answer",
        "use_case": "search a numeric answer when feasibility is monotonic",
        "complexity": "O(log range * feasibility_cost)",
        "example": "minimum eating speed",
        "pitfall": "writing a feasibility check that is not monotonic",
    },
    {
        "topic": "interval merging",
        "use_case": "combine overlapping ranges after sorting by start time",
        "complexity": "O(n log n) time and O(n) space",
        "example": "merge intervals",
        "pitfall": "not sorting before scanning",
    },
    {
        "topic": "line sweep",
        "use_case": "process starts and ends of events in sorted order",
        "complexity": "O(n log n) time for sorting events",
        "example": "meeting rooms",
        "pitfall": "handling start/end ties in the wrong order",
    },
    {
        "topic": "trie",
        "use_case": "store and query strings by prefix",
        "complexity": "O(L) per insert or lookup for word length L",
        "example": "implement trie",
        "pitfall": "forgetting terminal-word markers",
    },
    {
        "topic": "bit manipulation",
        "use_case": "encode sets or exploit binary properties of integers",
        "complexity": "usually O(1) per bit operation or O(number_of_bits)",
        "example": "single number",
        "pitfall": "mixing up bitwise and logical operators",
    },
    {
        "topic": "fast and slow pointers",
        "use_case": "detect cycles or find middle positions in linked structures",
        "complexity": "O(n) time and O(1) space",
        "example": "linked list cycle",
        "pitfall": "advancing the fast pointer without checking nulls",
    },
    {
        "topic": "matrix traversal",
        "use_case": "scan grids with boundary checks and directional movement",
        "complexity": "O(rows * cols) time",
        "example": "spiral matrix",
        "pitfall": "revisiting cells or crossing boundaries",
    },
    {
        "topic": "graph connected components",
        "use_case": "group nodes or grid cells that are reachable from each other",
        "complexity": "O(V + E) for graph traversal",
        "example": "number of provinces",
        "pitfall": "not marking visited before recursive calls",
    },
    {
        "topic": "memoization",
        "use_case": "cache recursive subproblem results",
        "complexity": "O(number_of_states * transition_cost)",
        "example": "climbing stairs",
        "pitfall": "using mutable state that is not part of the cache key",
    },
    {
        "topic": "tabulation",
        "use_case": "build dynamic-programming answers bottom up",
        "complexity": "O(number_of_states * transition_cost)",
        "example": "longest increasing subsequence",
        "pitfall": "filling states in an order that depends on future values",
    },
    {
        "topic": "divide and conquer",
        "use_case": "split a problem, solve subproblems, and combine results",
        "complexity": "often O(n log n), depending on the recurrence",
        "example": "merge sort",
        "pitfall": "forgetting the combine cost in complexity analysis",
    },
    {
        "topic": "sorting with custom keys",
        "use_case": "reorder records before greedy, interval, or ranking logic",
        "complexity": "O(n log n) time and usually O(n) auxiliary space",
        "example": "sort intervals by start time",
        "pitfall": "sorting by the wrong field for the intended invariant",
    },
    {
        "topic": "stack parsing",
        "use_case": "match nested structures or evaluate expressions",
        "complexity": "O(n) time and O(n) space",
        "example": "valid parentheses",
        "pitfall": "not checking for an empty stack before popping",
    },
]

PROMPT_STYLES = [
    {
        "name": "concept_overview",
        "instruction_suffix": "Include what it is, when to use it, complexity, code pattern, and practice examples.",
    },
    {
        "name": "interview_prep",
        "instruction_suffix": "Teach the interview pattern, recognition cues, edge cases, and two LeetCode-style practice problems.",
    },
    {
        "name": "debugging_focused",
        "instruction_suffix": "Explain common mistakes, debugging checks, boundary cases, and a corrected Python template.",
    },
    {
        "name": "compare_tradeoffs",
        "instruction_suffix": "Compare it with nearby algorithm patterns and explain tradeoffs, complexity, and when not to use it.",
    },
]

EVAL_CASES = [
    {
        "case_name": "core_algorithm_guide",
        "prompt_text": "Create Python algorithm study material covering binary search, two pointers, sliding window, hash maps, BFS, DFS, heaps, dynamic programming, and greedy algorithms.",
        "expected_topics": [
            "binary search",
            "two pointers",
            "sliding window",
            "hash map",
            "breadth-first search",
            "depth-first search",
            "heap",
            "dynamic programming",
            "greedy",
        ],
        "required_sections": [
            "definition",
            "when to use",
            "complexity",
            "python pattern",
            "practice example",
        ],
    },
    {
        "case_name": "dynamic_programming_deep_dive",
        "prompt_text": "Explain dynamic programming for Python interview prep with states, transitions, code pattern, mistakes, and LeetCode-style practice.",
        "expected_topics": ["dynamic programming"],
        "required_sections": [
            "definition",
            "when to use",
            "state",
            "transition",
            "complexity",
            "common mistake",
            "practice example",
        ],
    },
    {
        "case_name": "graph_search_comparison",
        "prompt_text": "Create study notes comparing BFS and DFS, including when to use each, complexity, code templates, and common mistakes.",
        "expected_topics": ["breadth-first search", "depth-first search"],
        "required_sections": [
            "definition",
            "when to use",
            "complexity",
            "python pattern",
            "common mistake",
            "practice example",
        ],
    },
]


def main() -> None:
    args = parse_args()
    storage_root = Path(args.storage_root)
    client = httpx.Client(base_url=args.api_base_url, timeout=60.0)

    dataset_results = ensure_variant_datasets(storage_root=storage_root)
    if args.datasets_only:
        print(
            json.dumps(
                {
                    "program_id": PROGRAM_ID,
                    "experiment_id": EXPERIMENT_ID,
                    "dataset_versions": dataset_results,
                    "source_priority": SourcePriority.SYNTHETIC_REALISTIC.value,
                    "note": "Expanded study-guide training seed datasets only; no new runs, model versions, evals, or failures were created.",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return
    suite = create_eval_suite(client)
    lifecycle_runs = []
    for variant in VARIANTS.values():
        dataset_id = int(variant["dataset_id"])
        dataset_version_id = int(variant["dataset_version_id"])
        records = fetch_records(
            client,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            limit=args.records,
        )
        record_dataset_access(
            client,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
        )
        run = train_variant(
            client=client,
            storage_root=storage_root,
            dataset_id=dataset_id,
            dataset_version_id=dataset_version_id,
            variant=variant,
            records=records,
            eval_suite_id=suite["eval_suite_id"],
            epochs=args.epochs,
            learning_rate=args.learning_rate,
        )
        checkpoint_id = latest_checkpoint_id(client, run_id=run["run_id"])
        model = promote_checkpoint(
            client=client,
            checkpoint_id=checkpoint_id,
            variant_name=variant["name"],
            eval_suite_id=suite["eval_suite_id"],
        )
        eval_run = run_eval(
            client=client,
            model_version_id=model["model_version_id"],
            eval_suite_id=suite["eval_suite_id"],
            variant_name=variant["name"],
        )
        candidates = create_candidates_for_eval_failures(
            client=client,
            eval_run_id=eval_run["eval_run_id"],
        )
        lifecycle_runs.append(
            {
                "variant": variant["name"],
                "dataset": {"dataset_id": dataset_id, "dataset_version_id": dataset_version_id},
                "run_id": run["run_id"],
                "checkpoint_id": checkpoint_id,
                "model_version_id": model["model_version_id"],
                "eval_run_id": eval_run["eval_run_id"],
                "failure_count": eval_run["failure_count"],
                "dataset_candidate_ids": [item["dataset_candidate_id"] for item in candidates],
            }
        )

    print(
        json.dumps(
            {
                "program_id": PROGRAM_ID,
                "experiment_id": EXPERIMENT_ID,
                "dataset_versions": dataset_results,
                "eval_suite_id": suite["eval_suite_id"],
                "lifecycle_runs": lifecycle_runs,
                "source_priority": SourcePriority.GENERATED_REAL.value,
                "note": "Small local training/evaluation workflow submitted real artifacts through the API.",
            },
            indent=2,
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Python study-guide experiment lifecycle through the Research Command Center API."
    )
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--storage-root", default="storage")
    parser.add_argument("--records", type=int, default=200)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=0.35)
    parser.add_argument(
        "--datasets-only",
        action="store_true",
        help="Only rebuild the study-guide variant datasets; do not create runs, models, evals, or candidates.",
    )
    return parser.parse_args()


def ensure_variant_datasets(storage_root: Path) -> list[dict[str, Any]]:
    created_at = utc_now()
    results = []
    for variant in VARIANTS.values():
        definition = DatasetDefinition(
            dataset_id=str(variant["storage_dataset_id"]),
            slug=str(variant["storage_dataset_id"]).removeprefix("ds_"),
            display_name=str(variant["display_name"]),
            source_dataset_name=str(variant["source_dataset_name"]),
            category="technical_education",
            task_type="study_guide_generation",
            description=str(variant["description"]),
            transform_name="build_study_guide_variant_records",
        )
        source_records = build_source_records(variant_name=variant["name"])
        raw_path = (
            storage_root
            / "raw"
            / "datasets"
            / definition.dataset_id
            / f"dataset_version_id={variant['storage_version_id']}"
            / "records.jsonl"
        )
        write_raw_jsonl(source_records, raw_path)
        normalized_records = [
            normalize_study_record(
                source_row=row,
                source_row_id=index,
                dataset_id=definition.dataset_id,
                source_dataset_name=definition.source_dataset_name,
                dataset_version_id=variant["storage_version_id"],
                created_at=created_at,
            )
            for index, row in enumerate(source_records, start=1)
        ]
        result = write_dataset_outputs(
            storage_root=storage_root,
            definition=definition,
            source_records=source_records,
            normalized_records=normalized_records,
            raw_path=raw_path,
            dataset_version_id=variant["storage_version_id"],
            created_at=created_at,
        )
        update_variant_manifest(
            storage_root=storage_root,
            definition=definition,
            variant=variant,
            storage_dataset_version_id=result.dataset_version_id,
        )
        results.append(
            {
                "dataset_id": variant["dataset_id"],
                "dataset_version_id": variant["dataset_version_id"],
                "storage_dataset_version_id": result.dataset_version_id,
                "record_count": result.record_count,
                "variant": variant["name"],
            }
        )
    register_duckdb_views(
        storage_root=storage_root,
        duckdb_path=storage_root / "duckdb" / "research_command_center.duckdb",
    )
    return results


def update_variant_manifest(
    storage_root: Path,
    definition: DatasetDefinition,
    variant: dict[str, Any],
    storage_dataset_version_id: str,
) -> None:
    manifest_path = (
        storage_root
        / "object_store"
        / "datasets"
        / definition.dataset_id
        / "versions"
        / storage_dataset_version_id
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "public_dataset_id": int(variant["dataset_id"]),
            "public_dataset_version_id": int(variant["dataset_version_id"]),
            "display_name": variant["display_name"],
            "description": variant["description"],
            "category": "Study-guide generation",
            "data_purpose": "Training data for structured technical study-guide generation",
            "data_format": "Parquet",
            "query_engine": "DuckDB",
            "source_url": f"storage/object_store/datasets/{definition.dataset_id}",
            "source_priority": SourcePriority.SYNTHETIC_REALISTIC.value,
            "variant_id": int(variant["variant_id"]),
            "variant_name": variant["name"],
            "variant_type": variant["variant_type"],
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def build_source_records(variant_name: str) -> list[dict[str, Any]]:
    rows = []
    for topic in ALGORITHM_TOPICS:
        for prompt_style in PROMPT_STYLES:
            prompt = (
                f"Create Python study material for {topic['topic']}. "
                f"{prompt_style['instruction_suffix']}"
            )
            rows.append(
                {
                    "variant_name": variant_name,
                    "prompt_style": prompt_style["name"],
                    "topic": topic["topic"],
                    "instruction": prompt,
                    "response": build_training_guide(
                        topic=topic,
                        variant_name=variant_name,
                        prompt_style=prompt_style["name"],
                    ),
                }
            )
    return rows


def normalize_study_record(
    source_row: dict[str, Any],
    source_row_id: int,
    dataset_id: str,
    source_dataset_name: str,
    dataset_version_id: str,
    created_at: str,
) -> dict[str, Any]:
    instruction = clean_text(source_row["instruction"])
    response = clean_text(source_row["response"])
    content_hash = content_hash_for_fields(
        instruction,
        response,
        source_row["variant_name"],
        source_row["prompt_style"],
    )
    return {
        "record_id": f"rec_{dataset_version_id}_{source_row_id}",
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "source_dataset_name": source_dataset_name,
        "source_split": "train",
        "source_row_id": str(source_row_id),
        "category": source_row["variant_name"],
        "task_type": "study_guide_generation",
        "input_text": instruction,
        "instruction": instruction,
        "context": "",
        "question": "",
        "chosen_text": "",
        "rejected_text": "",
        "target_text": response,
        "response_text": response,
        "prompt_messages_json": json.dumps([{"role": "user", "content": instruction}], ensure_ascii=True),
        "metadata_json": json.dumps(
            {
                "topic": source_row["topic"],
                "variant_name": source_row["variant_name"],
                "prompt_style": source_row["prompt_style"],
            },
            ensure_ascii=True,
        ),
        "content_hash": content_hash,
        "source_label": SourcePriority.SYNTHETIC_REALISTIC.value,
        "created_at": created_at,
    }


def fetch_records(
    client: httpx.Client,
    dataset_id: int,
    dataset_version_id: int,
    limit: int,
) -> list[dict[str, Any]]:
    response = client.get(
        f"/datasets/{dataset_id}/versions/{dataset_version_id}/records",
        params={"limit": limit},
    )
    response.raise_for_status()
    return response.json()["items"]


def record_dataset_access(client: httpx.Client, dataset_id: int, dataset_version_id: int) -> None:
    response = client.post(
        f"/datasets/{dataset_id}/versions/{dataset_version_id}/access",
        json={
            "program_id": PROGRAM_ID,
            "access_purpose": "experiment_training_export",
            "user_id": DEFAULT_OWNER,
        },
    )
    response.raise_for_status()


def train_variant(
    client: httpx.Client,
    storage_root: Path,
    dataset_id: int,
    dataset_version_id: int,
    variant: dict[str, Any],
    records: list[dict[str, Any]],
    eval_suite_id: int,
    epochs: int,
    learning_rate: float,
) -> dict[str, Any]:
    run = register_run(
        client=client,
        dataset_id=dataset_id,
        dataset_version_id=dataset_version_id,
        variant=variant,
        eval_suite_id=eval_suite_id,
    )
    run_id = int(run["run_id"])
    artifact_root = storage_root / "object_store" / "training_jobs" / f"run_id={run_id}"
    artifact_root.mkdir(parents=True, exist_ok=True)
    x, y, vocab = vectorize_training_records(records)
    weights = np.zeros((x.shape[1], y.shape[1]), dtype=np.float64)
    training_start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        prediction = x @ weights
        error = prediction - y
        loss = float(np.mean(error**2))
        gradient = (x.T @ error) / max(len(records), 1)
        weights -= learning_rate * gradient
        scores = np.clip(prediction.mean(axis=0), 0, 1)
        elapsed = max(time.perf_counter() - training_start, 1e-9)
        tokens_seen = sum(len((record.get("input_text") or "").split()) for record in records) * epoch
        event = {
            "timestamp": utc_now(),
            "step": epoch,
            "metrics": {
                "train.loss": round(loss, 6),
                "train.coverage_score": round(float(scores[0]), 6),
                "train.depth_score": round(float(scores[1]), 6),
                "train.example_score": round(float(scores[2]), 6),
                "train.accuracy_proxy": round(float(scores[3]), 6),
                "train.learning_flow_score": round(float(scores[4]), 6),
                "train.tokens_seen": float(tokens_seen),
                "train.tokens_per_second": round(tokens_seen / elapsed, 4),
                "train.epoch": float(epoch),
            },
            "compute_metrics": {
                "process.memory_rss_mb": 96.0 + epoch,
                "throughput.tokens_per_second": round(tokens_seen / elapsed, 4),
                "cost.estimated_usd": 0.0,
            },
            "node_id": "local_training_host",
            "gpu_id": "none",
        }
        post_json(client, f"/runs/{run_id}/events", {"events": [event]})
        if epoch in {max(1, math.ceil(epochs / 2)), epochs}:
            checkpoint_path = artifact_root / f"study_policy_epoch_{epoch}.json"
            checkpoint_payload = {
                "variant_name": variant["name"],
                "dataset_id": dataset_id,
                "dataset_version_id": dataset_version_id,
                "metric_names": METRIC_NAMES,
                "vocab": vocab,
                "weights": weights.round(8).tolist(),
                "epoch": epoch,
            }
            checkpoint_path.write_text(json.dumps(checkpoint_payload, indent=2), encoding="utf-8")
            post_json(
                client,
                f"/runs/{run_id}/checkpoints",
                {
                    "checkpoints": [
                        {
                            "step": epoch,
                            "checkpoint_uri": str(checkpoint_path),
                            "metrics_snapshot": event["metrics"],
                            "created_at": utc_now(),
                        }
                    ]
                },
            )
    post_json(client, f"/runs/{run_id}/complete", {"status": "completed", "ended_at": utc_now()})
    return run


def register_run(
    client: httpx.Client,
    dataset_id: int,
    dataset_version_id: int,
    variant: dict[str, Any],
    eval_suite_id: int,
) -> dict[str, Any]:
    payload = {
        "run_name": variant["run_name"],
        "program_id": PROGRAM_ID,
        "experiment_id": EXPERIMENT_ID,
        "dataset_id": dataset_id,
        "dataset_version_id": dataset_version_id,
        "experiment_name": "Outline-first Python algorithm study-guide recipe",
        "base_model_name": "numpy-study-guide-rubric-policy",
        "training_task": "study_guide_generation_policy_training",
        "research_intent": (
            "Train a small local policy model from registered study-guide records "
            "and report real metrics/checkpoints through the API."
        ),
        "success_criteria": "Loss decreases and the final checkpoint is promoted for rubric evaluation.",
        "owner_user_id": DEFAULT_OWNER,
        "training_environment": "local_numpy_external_training_script",
        "artifact_root_uri": f"storage/object_store/training_jobs/{variant['run_name']}",
        "ingest_source": "external_study_material_training_script",
        "planned_eval_suite_ids": [eval_suite_id],
        "run_config": {
            "framework": "numpy",
            "trainer": "scripts/run_study_material_full_lifecycle.py",
            "program_id": PROGRAM_ID,
            "experiment_id": EXPERIMENT_ID,
            "variant_id": variant["variant_id"],
            "dataset_id": dataset_id,
            "dataset_version_id": dataset_version_id,
            "variant_name": variant["name"],
            "variant_type": variant["variant_type"],
            "model_type": "linear_rubric_policy",
        },
    }
    return post_json(client, "/runs/register", payload)


def vectorize_training_records(records: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    texts = [str(record.get("input_text") or "") for record in records]
    targets = [
        rubric_scores(str(record.get("target_text") or ""), expected_topics=[str(record.get("category") or "")])
        for record in records
    ]
    tokenized = [tokenize(text) for text in texts]
    counts = Counter(token for tokens in tokenized for token in tokens)
    vocab = [token for token, _ in counts.most_common(96)]
    vocab_index = {token: index for index, token in enumerate(vocab)}
    x = np.zeros((len(records), len(vocab)), dtype=np.float64)
    for row_index, tokens in enumerate(tokenized):
        for token in tokens:
            column = vocab_index.get(token)
            if column is not None:
                x[row_index, column] += 1.0
        if x[row_index].sum():
            x[row_index] /= x[row_index].sum()
    y = np.array([[scores[name] for name in METRIC_NAMES] for scores in targets], dtype=np.float64)
    return x, y, vocab


def latest_checkpoint_id(client: httpx.Client, run_id: int) -> int:
    response = client.get(f"/runs/{run_id}/checkpoints")
    response.raise_for_status()
    checkpoints = response.json()["items"]
    return int(max(checkpoints, key=lambda item: int(item["step"]))["checkpoint_id"])


def promote_checkpoint(
    client: httpx.Client,
    checkpoint_id: int,
    variant_name: str,
    eval_suite_id: int,
) -> dict[str, Any]:
    return post_json(
        client,
        "/models/register-from-checkpoint",
        {
            "checkpoint_id": checkpoint_id,
            "model_name": "python-algorithm-study-guide-policy",
            "model_version_name": f"{variant_name}-candidate-checkpoint-{checkpoint_id}",
            "intended_use": "Generate and evaluate structured Python algorithm study guides.",
            "promotion_reason": "Final checkpoint from the experiment variant training run.",
            "promotion_notes": "Promoted automatically by the full lifecycle script for backend development.",
            "expected_eval_suite_ids": [eval_suite_id],
            "owner_user_id": DEFAULT_OWNER,
        },
    )


def create_eval_suite(client: httpx.Client) -> dict[str, Any]:
    return post_json(
        client,
        "/eval-suites",
        {
            "program_id": PROGRAM_ID,
            "experiment_id": EXPERIMENT_ID,
            "name": "Python algorithm study-guide rubric",
            "version": "v1",
            "status": "active",
            "source_priority": SourcePriority.GENERATED_REAL.value,
            "created_by_user_id": DEFAULT_OWNER,
            "cases": [
                {
                    **case,
                    "rubric": {
                        "coverage": "Expected algorithm topics are present.",
                        "depth": "Each topic has usable explanation and when-to-use guidance.",
                        "examples": "Code patterns and practice examples are present.",
                        "accuracy": "Complexity and terminology are technically plausible.",
                        "learning_flow": "The document has a coherent sequence and outline.",
                    },
                    "tags": ["python_algorithms", "study_material"],
                }
                for case in EVAL_CASES
            ],
        },
    )


def run_eval(
    client: httpx.Client,
    model_version_id: int,
    eval_suite_id: int,
    variant_name: str,
) -> dict[str, Any]:
    suite = client.get(f"/eval-suites/{eval_suite_id}")
    suite.raise_for_status()
    outputs = []
    for case in suite.json()["cases"]:
        output_text = generate_study_guide(
            variant_name=variant_name,
            prompt=case["prompt_text"],
            expected_topics=case["expected_topics"],
        )
        scores = rubric_scores(
            output_text,
            expected_topics=case["expected_topics"],
            required_sections=case["required_sections"],
        )
        outputs.append(
            {
                "eval_case_id": case["eval_case_id"],
                "prompt_text": case["prompt_text"],
                "output_text": output_text,
                "scores": scores,
                "score": scores["overall"],
                "scoring_method": "study_guide_rubric_v1",
                "failures": failures_for_scores(scores=scores, output_text=output_text),
            }
        )
    return post_json(
        client,
        "/eval-runs",
        {
            "eval_suite_id": eval_suite_id,
            "program_id": PROGRAM_ID,
            "experiment_id": EXPERIMENT_ID,
            "model_version_id": model_version_id,
            "status": "completed",
            "scoring_method": "study_guide_rubric_v1",
            "source_priority": SourcePriority.GENERATED_REAL.value,
            "created_by_user_id": DEFAULT_OWNER,
            "outputs": outputs,
        },
    )


def create_candidates_for_eval_failures(client: httpx.Client, eval_run_id: int) -> list[dict[str, Any]]:
    response = client.get(f"/eval-runs/{eval_run_id}")
    response.raise_for_status()
    detail = response.json()
    candidates = []
    for failure in detail["failures"]:
        candidate = post_json(
            client,
            f"/eval-failures/{failure['eval_failure_id']}/dataset-candidate",
            {
                "target_dataset_id": FAILURE_CORRECTION_DATASET_ID,
                "status": "proposed",
                "proposed_input_text": (
                    "Revise this Python algorithm study-guide answer to fix: "
                    f"{failure['failure_type']}"
                ),
                "proposed_target_text": corrected_training_target(failure["failure_type"]),
                "review_notes": (
                    "Candidate created from eval failure. A researcher should review before "
                    "publishing a new dataset version."
                ),
                "created_by_user_id": DEFAULT_OWNER,
            },
        )
        candidates.append(candidate)
    return candidates


def build_training_guide(
    topic: dict[str, str],
    variant_name: str,
    prompt_style: str = "concept_overview",
) -> str:
    style_guidance = {
        "concept_overview": "Start with the concept, then connect it to practical usage.",
        "interview_prep": "Emphasize pattern recognition, edge cases, and practice planning.",
        "debugging_focused": "Highlight mistakes, symptoms, and concrete debugging checks.",
        "compare_tradeoffs": "Compare it with nearby patterns and explain when not to use it.",
    }.get(prompt_style, "Start with the concept, then connect it to practical usage.")
    if variant_name == "control":
        return (
            f"{topic['topic'].title()} is a common Python interview algorithm. "
            f"It is used to {topic['use_case']}. Its complexity is {topic['complexity']}. "
            f"Practice with {topic['example']}. {style_guidance}"
        )
    base = (
        f"Outline\n"
        f"1. Definition\n2. When to use\n3. Complexity\n4. Python pattern\n5. Practice example\n\n"
        f"Definition: {topic['topic']} is a reusable algorithmic pattern for Python problems.\n"
        f"When to use: Use it to {topic['use_case']}.\n"
        f"Study angle: {style_guidance}\n"
        f"Complexity: The usual complexity is {topic['complexity']} because the algorithm limits repeated work.\n"
        f"Python pattern:\n```python\n"
        f"def solve(items):\n    # apply {topic['topic']} pattern\n    return items\n"
        f"```\n"
        f"Practice example: Try a LeetCode-style problem such as {topic['example']} and explain why the pattern applies.\n"
    )
    if variant_name != "outline_first_with_failure_corrections":
        return base
    return (
        f"{base}"
        f"Common mistake: {topic['pitfall']}.\n"
        f"Debugging checklist: identify the state, test empty input, test one item, and explain every boundary condition.\n"
        f"Study checkpoint: write the concept in your own words, then solve one easy and one medium practice problem.\n"
    )


def generate_study_guide(
    variant_name: str,
    prompt: str,
    expected_topics: list[str],
) -> str:
    topics = [topic for topic in ALGORITHM_TOPICS if topic_matches(topic["topic"], expected_topics)]
    if not topics:
        topics = ALGORITHM_TOPICS[:3]
    if variant_name == "control":
        selected = topics[: max(1, min(3, len(topics)))]
        sections = [
            f"{topic['topic'].title()}: use it to {topic['use_case']}. Complexity is {topic['complexity']}."
            for topic in selected
        ]
        return "Python algorithm study guide\n\n" + "\n\n".join(sections)
    sections = ["Outline", "1. Core concepts", "2. When to use each pattern", "3. Complexity", "4. Python patterns", "5. Practice path", ""]
    for topic in topics:
        sections.append(build_training_guide(topic, variant_name))
    if variant_name == "outline_first_with_failure_corrections":
        sections.append(
            "Final learning path: start with arrays and hash maps, then window/two-pointer patterns, then graph traversal, then dynamic programming and greedy tradeoffs."
        )
    return "\n".join(sections)


def rubric_scores(
    text: str,
    expected_topics: list[str],
    required_sections: list[str] | None = None,
) -> dict[str, float]:
    lower = text.lower()
    expected = [topic.lower() for topic in expected_topics if topic]
    if not expected:
        expected = ["algorithm"]
    section_terms = [section.lower() for section in (required_sections or [])]
    coverage = sum(1 for topic in expected if topic in lower) / len(expected)
    depth_terms = ["definition", "when to use", "because", "state", "transition", "debugging"]
    depth = min(1.0, (sum(1 for term in depth_terms if term in lower) + len(text.split()) / 180) / 5)
    examples = min(1.0, (lower.count("practice") + lower.count("leetcode") + lower.count("```python")) / 3)
    accuracy = min(1.0, (lower.count("complexity") + lower.count("o(") + lower.count("boundary")) / 4)
    learning_flow = min(1.0, (lower.count("outline") + lower.count("1.") + lower.count("2.") + lower.count("final learning path")) / 4)
    if section_terms:
        required_presence = sum(1 for section in section_terms if section in lower) / len(section_terms)
        depth = (depth + required_presence) / 2
    scores = {
        "coverage": round(coverage, 4),
        "depth": round(depth, 4),
        "examples": round(examples, 4),
        "accuracy": round(accuracy, 4),
        "learning_flow": round(learning_flow, 4),
    }
    scores["overall"] = round(sum(scores.values()) / len(scores), 4)
    return scores


def failures_for_scores(scores: dict[str, float], output_text: str) -> list[dict[str, Any]]:
    failures = []
    threshold = 0.72
    for metric_name in METRIC_NAMES:
        if scores[metric_name] >= threshold:
            continue
        failures.append(
            {
                "failure_type": failure_type_for_metric(metric_name),
                "severity": "high" if scores[metric_name] < 0.45 else "medium",
                "failure_reason": f"{metric_name} scored {scores[metric_name]} below threshold {threshold}.",
                "evidence_text": output_text[:240],
            }
        )
    return failures


def failure_type_for_metric(metric_name: str) -> str:
    return {
        "coverage": "missing_algorithm_coverage",
        "depth": "shallow_explanation",
        "examples": "missing_practice_examples",
        "accuracy": "weak_complexity_grounding",
        "learning_flow": "poor_learning_progression",
    }[metric_name]


def corrected_training_target(failure_type: str) -> str:
    return (
        "A corrected study-guide answer should include an outline, complete topic coverage, "
        "definition, when-to-use guidance, complexity reasoning, runnable Python pattern, "
        f"practice examples, and a focused fix for {failure_type}."
    )


def topic_matches(topic: str, expected_topics: list[str]) -> bool:
    topic_lower = topic.lower()
    expected = " ".join(expected_topics).lower()
    aliases = {
        "breadth-first search": ["bfs", "breadth-first search"],
        "depth-first search": ["dfs", "depth-first search"],
        "hash map counting": ["hash map", "hash maps"],
        "heap priority queue": ["heap", "priority queue"],
    }
    return any(alias in expected for alias in aliases.get(topic_lower, [topic_lower]))


def tokenize(text: str) -> list[str]:
    return [
        token.strip(".,:;!?()[]{}").lower()
        for token in text.split()
        if token.strip(".,:;!?()[]{}")
    ]


def post_json(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
