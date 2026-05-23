from __future__ import annotations

from pathlib import Path

from app.runs.ingestion import seed_demo_runs


def main() -> None:
    results = seed_demo_runs(storage_root=Path("storage"))
    for result in results:
        print(
            f"seeded run_id={result.run_id} dataset_version_id={result.dataset_version_id} "
            f"checkpoints={result.checkpoint_count}"
        )


if __name__ == "__main__":
    main()
