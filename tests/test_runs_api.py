from pathlib import Path

from fastapi.testclient import TestClient

from app.experiments.lifecycle import register_experiment
from app.experiments.repository import ExperimentRepository
from app.main import app
from app.research_programs.lifecycle import register_research_program
from app.research_programs.repository import ResearchProgramRepository
from app.runs.api import get_run_repository, get_run_storage_root
from app.runs.ingestion import seed_demo_runs
from app.runs.repository import RunRepository


def test_runs_api_exposes_researcher_submitted_run_data(tmp_path: Path) -> None:
    results = seed_demo_runs(storage_root=tmp_path)

    def override_repository() -> RunRepository:
        return RunRepository(duckdb_path=Path(results[0].duckdb_path), storage_root=tmp_path)

    app.dependency_overrides[get_run_repository] = override_repository
    app.dependency_overrides[get_run_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        list_response = client.get("/runs")
        assert list_response.status_code == 200
        runs = list_response.json()["items"]
        assert len(runs) == 3
        assert {run["status"] for run in runs} == {"completed", "failed"}
        assert runs[0]["ingest_source"] == "researcher_sdk_demo"
        assert runs[0]["health_summary"]["health_score"] > 0

        detail_response = client.get("/runs/1")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["dataset_id"] == 1
        assert detail["dataset_version_id"] == 1
        assert detail["raw_ingest_summary"]["source_priority"] == "SYNTHETIC_REALISTIC"
        assert detail["metric_summary"]["final_loss"] < detail["metric_summary"]["initial_loss"]
        assert len(detail["checkpoints"]) == 3
        assert detail["lineage"][0]["source_type"] == "dataset_version"
        assert detail["lineage"][-1]["target_type"] == "checkpoint"

        metrics_response = client.get("/runs/1/metrics")
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()["items"]
        assert {"run_id", "timestamp", "step", "metric_name", "metric_value"}.issubset(metrics[0])
        assert any(metric["metric_name"] == "train.loss" for metric in metrics)

        checkpoints_response = client.get("/runs/1/checkpoints")
        assert checkpoints_response.status_code == 200
        checkpoints = checkpoints_response.json()["items"]
        assert checkpoints[0]["checkpoint_uri"].startswith("s3://research-runs/")
    finally:
        app.dependency_overrides.clear()


def test_run_registration_append_and_completion_flow(tmp_path: Path) -> None:
    from app.datasets.dolly_ingestion import ingest_dolly_records

    ingest_dolly_records(
        storage_root=tmp_path,
        source_records=[
            {
                "instruction": f"Classify example {index}",
                "context": "Synthetic unit-test source row for registration validation.",
                "response": "This record exercises the registered dataset workflow.",
                "category": "classification" if index % 2 else "open_qa",
            }
            for index in range(40)
        ],
    )
    register_research_program(
        storage_root=tmp_path,
        payload={
            "program_name": "Run registration linking test",
            "status": "active",
            "researcher_names": ["Lena Keys"],
        },
    )
    register_experiment(
        storage_root=tmp_path,
        payload={
            "program_id": 1,
            "experiment_name": "Run registration experiment",
            "experiment_description": "Validate run-to-experiment linkage.",
            "research_question": "Can externally reported runs attach to an experiment?",
            "hypothesis": "A run that provides experiment_id should update experiment lineage.",
            "experiment_type": "run_lineage_validation",
            "status": "active",
            "owner_name": "Lena Keys",
            "linked_datasets": [{"dataset_id": 1, "dataset_version_id": 1}],
        },
    )

    def override_repository() -> RunRepository:
        return RunRepository(
            duckdb_path=tmp_path / "duckdb" / "research_command_center.duckdb",
            storage_root=tmp_path,
        )

    app.dependency_overrides[get_run_repository] = override_repository
    app.dependency_overrides[get_run_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        missing_experiment_response = client.post(
            "/runs/register",
            json={
                "run_name": "missing-experiment-id",
                "program_id": 1,
                "dataset_id": 1,
                "dataset_version_id": 1,
                "base_model_name": "numpy-softmax-text-classifier",
                "training_task": "instruction_category_classification",
                "research_intent": "Exercise validation.",
                "owner_user_id": "user_test",
                "training_environment": "local_test_process",
                "artifact_root_uri": "storage/object_store/test/run-missing-experiment",
            },
        )
        assert missing_experiment_response.status_code == 400
        assert "experiment_id is required" in missing_experiment_response.json()["detail"]

        register_response = client.post(
            "/runs/register",
            json={
                "run_name": "api-registered-real-run",
                "program_id": 1,
                "experiment_id": 1,
                "dataset_id": 1,
                "dataset_version_id": 1,
                "base_model_name": "numpy-softmax-text-classifier",
                "training_task": "instruction_category_classification",
                "research_intent": "Exercise the run registration and append workflow.",
                "owner_user_id": "user_test",
                "training_environment": "local_test_process",
                "artifact_root_uri": "storage/object_store/test/run",
                "run_config": {"learning_rate": 0.1},
            },
        )
        assert register_response.status_code == 200
        run_id = register_response.json()["run_id"]
        assert run_id == 1
        assert register_response.json()["program_id"] == 1
        assert register_response.json()["experiment_id"] == 1

        event_response = client.post(
            f"/runs/{run_id}/events",
            json={
                "events": [
                    {
                        "timestamp": "2026-05-23T03:00:00Z",
                        "step": 1,
                        "metrics": {
                            "train.loss": 1.2,
                            "train.accuracy": 0.4,
                            "train.tokens_seen": 128,
                        },
                        "compute_metrics": {
                            "process.memory_rss_mb": 120.0,
                            "throughput.tokens_per_second": 256.0,
                            "cost.estimated_usd": 0.0,
                        },
                    }
                ]
            },
        )
        assert event_response.status_code == 200
        assert event_response.json()["appended_count"] == 1

        checkpoint_response = client.post(
            f"/runs/{run_id}/checkpoints",
            json={
                "checkpoints": [
                    {
                        "step": 1,
                        "checkpoint_uri": "storage/object_store/test/run/checkpoint_step_1.npz",
                        "metrics_snapshot": {"train.loss": 1.2},
                    }
                ]
            },
        )
        assert checkpoint_response.status_code == 200

        complete_response = client.post(f"/runs/{run_id}/complete", json={"status": "completed"})
        assert complete_response.status_code == 200

        detail = client.get(f"/runs/{run_id}").json()
        assert detail["source_priority"] == "GENERATED_REAL"
        assert detail["metric_summary"]["final_loss"] == 1.2
        assert detail["compute_summary"]["avg_process_memory_mb"] == 120.0
        assert detail["checkpoints"][0]["checkpoint_id"] == 1001

        program = ResearchProgramRepository(
            duckdb_path=tmp_path / "duckdb" / "research_command_center.duckdb",
            storage_root=tmp_path,
        ).get_program(1)
        assert program is not None
        assert program["linked_datasets"] == [{"dataset_id": 1, "dataset_version_id": 1}]
        assert program["linked_experiment_ids"] == [1]
        assert program["linked_run_ids"] == [run_id]

        experiment = ExperimentRepository(
            duckdb_path=tmp_path / "duckdb" / "research_command_center.duckdb",
            storage_root=tmp_path,
        ).get_experiment(1)
        assert experiment is not None
        assert experiment["linked_datasets"] == [{"dataset_id": 1, "dataset_version_id": 1}]
        assert experiment["linked_run_ids"] == [run_id]

        search_response = client.get(
            "/checkpoints",
            params={
                "dataset_id": 1,
                "dataset_version_id": 1,
                "ranking_metric": "train.loss",
                "direction": "asc",
            },
        )
        assert search_response.status_code == 200
        checkpoints = search_response.json()["items"]
        assert checkpoints[0]["checkpoint_id"] == 1001
        assert checkpoints[0]["run_id"] == run_id
        assert checkpoints[0]["is_best_for_filter"] is True
        assert checkpoints[0]["metrics_snapshot"]["train.loss"] == 1.2
    finally:
        app.dependency_overrides.clear()
