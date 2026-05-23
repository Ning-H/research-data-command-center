from __future__ import annotations

import argparse
import json
import math
import re
import resource
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_']+")


def main() -> None:
    args = parse_args()
    client = httpx.Client(base_url=args.api_base_url, timeout=30.0)
    if args.program_id is not None:
        record_dataset_access(
            client=client,
            program_id=args.program_id,
            dataset_id=args.dataset_id,
            dataset_version_id=args.dataset_version_id,
        )
    records = fetch_records(
        client=client,
        dataset_id=args.dataset_id,
        dataset_version_id=args.dataset_version_id,
        limit=args.records,
    )
    if len(records) < 20:
        raise SystemExit("Need at least 20 dataset records to train the demo classifier.")

    x, y, vocab, labels, token_counts = vectorize(records=records, vocab_size=args.vocab_size)
    run = register_run(client=client, args=args, label_count=len(labels), vocab_size=len(vocab))
    run_id = int(run["run_id"])
    artifact_root = Path("storage/object_store/training_jobs") / f"run_id={run_id}"
    artifact_root.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    weights = rng.normal(0, 0.01, size=(x.shape[1], len(labels)))
    bias = np.zeros(len(labels))
    step = 0
    tokens_seen = 0
    training_start = time.perf_counter()
    event: dict[str, Any] | None = None
    last_checkpoint: dict[str, Any] | None = None

    for epoch in range(1, args.epochs + 1):
        order = rng.permutation(len(x))
        for batch_start in range(0, len(order), args.batch_size):
            step += 1
            batch_indices = order[batch_start : batch_start + args.batch_size]
            xb = x[batch_indices]
            yb = y[batch_indices]
            batch_tokens = int(sum(token_counts[index] for index in batch_indices))

            logits = xb @ weights + bias
            probabilities = softmax(logits)
            grad_logits = probabilities
            grad_logits[np.arange(len(yb)), yb] -= 1
            grad_logits /= len(yb)
            weights -= args.learning_rate * (xb.T @ grad_logits)
            bias -= args.learning_rate * grad_logits.sum(axis=0)
            tokens_seen += batch_tokens

        full_probabilities = softmax(x @ weights + bias)
        loss = cross_entropy(full_probabilities, y)
        accuracy = float((full_probabilities.argmax(axis=1) == y).mean())
        total_elapsed = max(time.perf_counter() - training_start, 1e-9)
        tokens_per_second = tokens_seen / total_elapsed
        estimated_cost = (total_elapsed / 3600) * args.hourly_rate_usd
        event = {
            "timestamp": utc_now(),
            "step": step,
            "metrics": {
                "train.loss": round(loss, 6),
                "train.accuracy": round(accuracy, 6),
                "train.learning_rate": args.learning_rate,
                "train.tokens_seen": float(tokens_seen),
                "train.tokens_per_second": round(tokens_per_second, 4),
                "train.epoch": float(epoch),
            },
            "compute_metrics": {
                "process.memory_rss_mb": round(memory_rss_mb(), 4),
                "process.cpu_user_seconds": round(resource.getrusage(resource.RUSAGE_SELF).ru_utime, 6),
                "process.cpu_system_seconds": round(resource.getrusage(resource.RUSAGE_SELF).ru_stime, 6),
                "throughput.tokens_per_second": round(tokens_per_second, 4),
                "cost.estimated_usd": round(estimated_cost, 8),
            },
            "node_id": "local_m1",
            "gpu_id": "none",
        }
        post_json(client, f"/runs/{run_id}/events", {"events": [event]})

        if epoch in checkpoint_epochs(args.epochs):
            checkpoint_path = artifact_root / f"checkpoint_epoch_{epoch}_step_{step}.npz"
            np.savez(
                checkpoint_path,
                weights=weights,
                bias=bias,
                vocab=np.array(vocab),
                labels=np.array(labels),
            )
            last_checkpoint = {
                "step": step,
                "checkpoint_uri": str(checkpoint_path),
                "metrics_snapshot": event["metrics"] if event else {},
                "created_at": utc_now(),
            }
            post_json(client, f"/runs/{run_id}/checkpoints", {"checkpoints": [last_checkpoint]})

    post_json(client, f"/runs/{run_id}/complete", {"status": "completed", "ended_at": utc_now()})
    manifest = {
        "run_id": run_id,
        "program_id": args.program_id,
        "dataset_id": args.dataset_id,
        "dataset_version_id": args.dataset_version_id,
        "records": len(records),
        "labels": labels,
        "vocab_size": len(vocab),
        "last_checkpoint": last_checkpoint,
        "source_priority": "GENERATED_REAL",
    }
    (artifact_root / "training_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a tiny text classifier from registered dataset records and log to the platform API."
    )
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--dataset-id", type=int, default=1)
    parser.add_argument("--dataset-version-id", type=int, default=1)
    parser.add_argument("--program-id", type=int, default=None)
    parser.add_argument("--records", type=int, default=160)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--vocab-size", type=int, default=384)
    parser.add_argument("--learning-rate", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hourly-rate-usd", type=float, default=0.0)
    parser.add_argument("--run-name", default="dolly-real-api-text-classifier-v1")
    return parser.parse_args()


def fetch_records(
    client: httpx.Client,
    dataset_id: int,
    dataset_version_id: int,
    limit: int,
) -> list[dict[str, Any]]:
    response = client.get(f"/datasets/{dataset_id}/versions/{dataset_version_id}/records", params={"limit": limit})
    response.raise_for_status()
    return response.json()["items"]


def record_dataset_access(
    client: httpx.Client,
    program_id: int,
    dataset_id: int,
    dataset_version_id: int,
) -> None:
    response = client.post(
        f"/datasets/{dataset_id}/versions/{dataset_version_id}/access",
        json={
            "program_id": program_id,
            "access_purpose": "training_export",
            "user_id": "user_demo_owner",
        },
    )
    response.raise_for_status()


def register_run(
    client: httpx.Client,
    args: argparse.Namespace,
    label_count: int,
    vocab_size: int,
) -> dict[str, Any]:
    payload = {
        "run_name": args.run_name,
        "experiment_name": "real-api-ingestion-smoke-test",
        "program_id": args.program_id,
        "dataset_id": args.dataset_id,
        "dataset_version_id": args.dataset_version_id,
        "base_model_name": "numpy-softmax-text-classifier",
        "training_task": "instruction_category_classification",
        "research_intent": (
            "Verify that an external training job can read registered Parquet-backed "
            "dataset records and submit real run metrics/checkpoints through the API."
        ),
        "success_criteria": "Loss decreases and checkpoint metadata is linked to the run.",
        "owner_user_id": "user_demo_owner",
        "training_environment": "local_apple_m1_cpu_numpy",
        "artifact_root_uri": f"storage/object_store/training_jobs/{args.run_name}",
        "ingest_source": "external_training_script",
        "run_config": {
            "dataset_id": args.dataset_id,
            "dataset_version_id": args.dataset_version_id,
            "program_id": args.program_id,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "records": args.records,
            "vocab_size": vocab_size,
            "label_count": label_count,
            "trainer": "scripts/train_registered_text_classifier.py",
        },
    }
    return post_json(client, "/runs/register", payload)


def vectorize(
    records: list[dict[str, Any]],
    vocab_size: int,
) -> tuple[np.ndarray, np.ndarray, list[str], list[str], list[int]]:
    texts = [record_text(record) for record in records]
    labels = sorted({record["category"] or "uncategorized" for record in records})
    label_index = {label: index for index, label in enumerate(labels)}
    tokenized = [tokenize(text) for text in texts]
    vocabulary_counts = Counter(token for tokens in tokenized for token in tokens)
    vocab = [token for token, _ in vocabulary_counts.most_common(vocab_size)]
    vocab_index = {token: index for index, token in enumerate(vocab)}
    x = np.zeros((len(records), len(vocab)), dtype=np.float64)
    for row_index, tokens in enumerate(tokenized):
        if not tokens:
            continue
        for token in tokens:
            column = vocab_index.get(token)
            if column is not None:
                x[row_index, column] += 1.0
        row_sum = x[row_index].sum()
        if row_sum:
            x[row_index] /= row_sum
    y = np.array([label_index[record["category"] or "uncategorized"] for record in records])
    return x, y, vocab, labels, [len(tokens) for tokens in tokenized]


def record_text(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(field) or "")
        for field in ["instruction", "context", "question", "input_text", "target_text"]
    )


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def cross_entropy(probabilities: np.ndarray, labels: np.ndarray) -> float:
    clipped = np.clip(probabilities[np.arange(len(labels)), labels], 1e-12, 1.0)
    return float(-np.log(clipped).mean())


def checkpoint_epochs(total_epochs: int) -> set[int]:
    return {max(1, math.ceil(total_epochs / 2)), total_epochs}


def memory_rss_mb() -> float:
    # macOS reports ru_maxrss in bytes; Linux reports KiB. This project currently
    # runs locally on macOS, but keep the Linux branch for portability.
    raw = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return raw / (1024 * 1024) if raw > 10_000_000 else raw / 1024


def post_json(client: httpx.Client, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
