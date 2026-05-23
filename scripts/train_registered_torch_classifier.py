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
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from torch.utils.tensorboard import SummaryWriter


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
        raise SystemExit("Need at least 20 dataset records to train the PyTorch demo classifier.")

    x, y, vocab, labels, token_counts = vectorize(records=records, vocab_size=args.vocab_size)
    device = choose_device()
    run = register_run(
        client=client,
        args=args,
        label_count=len(labels),
        vocab_size=len(vocab),
        device=device,
    )
    run_id = int(run["run_id"])
    artifact_root = Path("storage/object_store/training_jobs") / f"run_id={run_id}"
    artifact_root.mkdir(parents=True, exist_ok=True)
    tensorboard_dir = artifact_root / "tensorboard"
    writer = SummaryWriter(log_dir=str(tensorboard_dir))

    generator = torch.Generator().manual_seed(args.seed)
    dataset = TensorDataset(
        torch.tensor(x, dtype=torch.float32),
        torch.tensor(y, dtype=torch.long),
        torch.tensor(token_counts, dtype=torch.long),
    )
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, generator=generator)
    model = nn.Linear(len(x[0]), len(labels)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    criterion = nn.CrossEntropyLoss()

    step = 0
    tokens_seen = 0
    training_start = time.perf_counter()
    last_checkpoint: dict[str, Any] | None = None

    try:
        for epoch in range(1, args.epochs + 1):
            model.train()
            for xb, yb, token_count_batch in loader:
                step += 1
                xb = xb.to(device)
                yb = yb.to(device)
                batch_tokens = int(token_count_batch.sum().item())

                optimizer.zero_grad(set_to_none=True)
                logits = model(xb)
                loss = criterion(logits, yb)
                loss.backward()
                optimizer.step()
                tokens_seen += batch_tokens

            metrics = evaluate(model=model, x=x, y=y, device=device, criterion=criterion)
            elapsed = max(time.perf_counter() - training_start, 1e-9)
            tokens_per_second = tokens_seen / elapsed
            estimated_cost = (elapsed / 3600) * args.hourly_rate_usd
            event = {
                "timestamp": utc_now(),
                "step": step,
                "metrics": {
                    "train.loss": round(metrics["loss"], 6),
                    "train.accuracy": round(metrics["accuracy"], 6),
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
                    **device_metrics(device),
                },
                "node_id": "local_training_host",
                "gpu_id": device.type,
            }
            writer.add_scalar("train/loss", metrics["loss"], step)
            writer.add_scalar("train/accuracy", metrics["accuracy"], step)
            writer.add_scalar("train/tokens_per_second", tokens_per_second, step)
            writer.add_scalar("system/memory_rss_mb", memory_rss_mb(), step)
            writer.add_scalar("cost/estimated_usd", estimated_cost, step)
            post_json(client, f"/runs/{run_id}/events", {"events": [event]})

            if epoch in checkpoint_epochs(args.epochs):
                checkpoint_path = artifact_root / f"torch_checkpoint_epoch_{epoch}_step_{step}.pt"
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "vocab": vocab,
                        "labels": labels,
                        "dataset_id": args.dataset_id,
                        "dataset_version_id": args.dataset_version_id,
                        "step": step,
                    },
                    checkpoint_path,
                )
                last_checkpoint = {
                    "step": step,
                    "checkpoint_uri": str(checkpoint_path),
                    "metrics_snapshot": event["metrics"],
                    "created_at": utc_now(),
                }
                post_json(client, f"/runs/{run_id}/checkpoints", {"checkpoints": [last_checkpoint]})
    finally:
        writer.flush()
        writer.close()

    post_json(client, f"/runs/{run_id}/complete", {"status": "completed", "ended_at": utc_now()})
    manifest = {
        "run_id": run_id,
        "program_id": args.program_id,
        "dataset_id": args.dataset_id,
        "dataset_version_id": args.dataset_version_id,
        "records": len(records),
        "labels": labels,
        "vocab_size": len(vocab),
        "device": device.type,
        "tensorboard_log_dir": str(tensorboard_dir),
        "last_checkpoint": last_checkpoint,
        "source_priority": "GENERATED_REAL",
        "trainer": "PyTorch",
    }
    (artifact_root / "torch_training_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a PyTorch text classifier from registered dataset records and log to the platform API."
    )
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--dataset-id", type=int, default=1)
    parser.add_argument("--dataset-version-id", type=int, default=1)
    parser.add_argument("--program-id", type=int, default=None)
    parser.add_argument("--records", type=int, default=200)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--vocab-size", type=int, default=512)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--hourly-rate-usd", type=float, default=0.0)
    parser.add_argument("--run-name", default="dolly-pytorch-text-classifier-v1")
    return parser.parse_args()


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
    device: torch.device,
) -> dict[str, Any]:
    payload = {
        "run_name": args.run_name,
        "experiment_name": "pytorch-real-api-ingestion",
        "program_id": args.program_id,
        "dataset_id": args.dataset_id,
        "dataset_version_id": args.dataset_version_id,
        "base_model_name": "pytorch-linear-text-classifier",
        "training_task": "instruction_category_classification",
        "research_intent": (
            "Verify that a standard PyTorch training job can read registered "
            "dataset records and submit real metrics/checkpoints through the API."
        ),
        "success_criteria": "Loss decreases, TensorBoard scalars are written, and checkpoints are linked to the run.",
        "owner_user_id": "user_demo_owner",
        "training_environment": "local_pytorch_training_job",
        "artifact_root_uri": f"storage/object_store/training_jobs/{args.run_name}",
        "ingest_source": "external_pytorch_training_script",
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
            "framework": "pytorch",
            "tracker": "tensorboard",
            "device": device.type,
            "trainer": "scripts/train_registered_torch_classifier.py",
        },
    }
    return post_json(client, "/runs/register", payload)


def vectorize(
    records: list[dict[str, Any]],
    vocab_size: int,
) -> tuple[list[list[float]], list[int], list[str], list[str], list[int]]:
    texts = [record_text(record) for record in records]
    labels = sorted({record["category"] or "uncategorized" for record in records})
    label_index = {label: index for index, label in enumerate(labels)}
    tokenized = [tokenize(text) for text in texts]
    vocabulary_counts = Counter(token for tokens in tokenized for token in tokens)
    vocab = [token for token, _ in vocabulary_counts.most_common(vocab_size)]
    vocab_index = {token: index for index, token in enumerate(vocab)}
    rows: list[list[float]] = []
    for tokens in tokenized:
        vector = [0.0] * len(vocab)
        for token in tokens:
            column = vocab_index.get(token)
            if column is not None:
                vector[column] += 1.0
        row_sum = sum(vector)
        if row_sum:
            vector = [value / row_sum for value in vector]
        rows.append(vector)
    y = [label_index[record["category"] or "uncategorized"] for record in records]
    return rows, y, vocab, labels, [len(tokens) for tokens in tokenized]


def evaluate(
    model: nn.Module,
    x: list[list[float]],
    y: list[int],
    device: torch.device,
    criterion: nn.Module,
) -> dict[str, float]:
    model.eval()
    with torch.no_grad():
        xb = torch.tensor(x, dtype=torch.float32, device=device)
        yb = torch.tensor(y, dtype=torch.long, device=device)
        logits = model(xb)
        loss = float(criterion(logits, yb).detach().cpu().item())
        accuracy = float((logits.argmax(dim=1) == yb).float().mean().detach().cpu().item())
    return {"loss": loss, "accuracy": accuracy}


def record_text(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(field) or "")
        for field in ["instruction", "context", "question", "input_text", "target_text"]
    )


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]


def choose_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def device_metrics(device: torch.device) -> dict[str, float]:
    if device.type == "cuda":
        return {
            "gpu.memory_used_gb": torch.cuda.max_memory_allocated() / (1024**3),
        }
    if device.type == "mps" and hasattr(torch, "mps"):
        try:
            return {
                "gpu.memory_used_gb": torch.mps.current_allocated_memory() / (1024**3),
            }
        except RuntimeError:
            return {}
    return {}


def checkpoint_epochs(total_epochs: int) -> set[int]:
    return {max(1, math.ceil(total_epochs / 2)), total_epochs}


def memory_rss_mb() -> float:
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
