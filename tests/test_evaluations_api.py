from pathlib import Path

from fastapi.testclient import TestClient

from app.dataset_candidates.api import (
    get_dataset_candidate_repository,
    get_dataset_candidate_storage_root,
)
from app.dataset_candidates.repository import DatasetCandidateRepository
from app.datasets.api import get_dataset_repository, get_dataset_storage_root
from app.datasets.repository import DatasetRepository
from app.evaluations.api import get_evaluation_repository, get_evaluation_storage_root
from app.evaluations.repository import EvaluationRepository
from app.experiments.api import get_experiment_repository, get_experiment_storage_root
from app.experiments.lifecycle import register_experiment
from app.experiments.repository import ExperimentRepository
from app.main import app
from app.models.api import get_model_repository, get_model_storage_root
from app.models.lifecycle import register_model_duckdb_views
from app.models.repository import ModelRepository
from app.research_programs.lifecycle import register_research_program
from app.runs.api import get_run_repository, get_run_storage_root
from app.runs.repository import RunRepository


def test_eval_run_failures_can_be_saved_as_dataset_candidates(tmp_path: Path) -> None:
    from app.datasets.dolly_ingestion import ingest_dolly_records

    ingest_dolly_records(
        storage_root=tmp_path,
        source_records=[
            {
                "instruction": f"Study guide example {index}",
                "context": "Unit-test source row for eval lifecycle validation.",
                "response": "This record supports the registered run workflow.",
                "category": "open_qa" if index % 2 else "classification",
            }
            for index in range(40)
        ],
    )
    register_research_program(
        storage_root=tmp_path,
        payload={
            "program_name": "Structured study guide program",
            "status": "active",
            "owner_name": "Lena Keys",
            "researcher_names": ["Lena Keys"],
        },
    )
    register_experiment(
        storage_root=tmp_path,
        payload={
            "program_id": 1,
            "experiment_name": "Outline-first study guide experiment",
            "experiment_description": "Validate eval lifecycle.",
            "research_question": "Can eval failures become dataset candidates?",
            "hypothesis": "Failures should become candidate records.",
            "experiment_type": "study_material_structure_comparison",
            "status": "active",
            "owner_name": "Lena Keys",
            "linked_datasets": [{"dataset_id": 1, "dataset_version_id": 1}],
        },
    )

    duckdb_path = tmp_path / "duckdb" / "research_command_center.duckdb"

    def override_run_repository() -> RunRepository:
        return RunRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    def override_model_repository() -> ModelRepository:
        register_model_duckdb_views(storage_root=tmp_path, duckdb_path=duckdb_path)
        return ModelRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    def override_evaluation_repository() -> EvaluationRepository:
        return EvaluationRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    def override_experiment_repository() -> ExperimentRepository:
        return ExperimentRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    def override_candidate_repository() -> DatasetCandidateRepository:
        return DatasetCandidateRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    def override_dataset_repository() -> DatasetRepository:
        return DatasetRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    app.dependency_overrides[get_run_repository] = override_run_repository
    app.dependency_overrides[get_run_storage_root] = lambda: tmp_path
    app.dependency_overrides[get_model_repository] = override_model_repository
    app.dependency_overrides[get_model_storage_root] = lambda: tmp_path
    app.dependency_overrides[get_evaluation_repository] = override_evaluation_repository
    app.dependency_overrides[get_evaluation_storage_root] = lambda: tmp_path
    app.dependency_overrides[get_experiment_repository] = override_experiment_repository
    app.dependency_overrides[get_experiment_storage_root] = lambda: tmp_path
    app.dependency_overrides[get_dataset_candidate_repository] = override_candidate_repository
    app.dependency_overrides[get_dataset_candidate_storage_root] = lambda: tmp_path
    app.dependency_overrides[get_dataset_repository] = override_dataset_repository
    app.dependency_overrides[get_dataset_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        run_response = client.post(
            "/runs/register",
            json={
                "run_name": "eval-source-run",
                "program_id": 1,
                "experiment_id": 1,
                "dataset_id": 1,
                "dataset_version_id": 1,
                "base_model_name": "study-guide-policy",
                "training_task": "study_guide_policy_training",
                "research_intent": "Create a checkpoint for eval validation.",
                "owner_user_id": "user_test",
                "training_environment": "local_test_process",
                "artifact_root_uri": "storage/object_store/test/eval-source-run",
                "run_config": {"framework": "numpy"},
            },
        )
        assert run_response.status_code == 200
        run_id = run_response.json()["run_id"]
        assert client.post(
            f"/runs/{run_id}/events",
            json={
                "events": [
                    {
                        "timestamp": "2026-05-23T05:00:00Z",
                        "step": 2,
                        "metrics": {"train.loss": 0.2, "train.accuracy": 0.8},
                    }
                ]
            },
        ).status_code == 200
        assert client.post(
            f"/runs/{run_id}/checkpoints",
            json={
                "checkpoints": [
                    {
                        "step": 2,
                        "checkpoint_uri": "storage/object_store/test/checkpoint.json",
                        "metrics_snapshot": {"train.loss": 0.2},
                    }
                ]
            },
        ).status_code == 200
        assert client.post(f"/runs/{run_id}/complete", json={"status": "completed"}).status_code == 200

        model_response = client.post(
            "/models/register-from-checkpoint",
            json={
                "checkpoint_id": 1001,
                "model_name": "study-guide-policy",
                "model_version_name": "candidate-checkpoint-1001",
            },
        )
        assert model_response.status_code == 200
        model_version_id = model_response.json()["model_version_id"]

        suite_response = client.post(
            "/eval-suites",
            json={
                "program_id": 1,
                "experiment_id": 1,
                "name": "Study guide rubric",
                "cases": [
                    {
                        "case_name": "Binary search guide",
                        "prompt_text": "Explain binary search.",
                        "expected_topics": ["binary search"],
                        "required_sections": ["definition", "complexity"],
                    }
                ],
            },
        )
        assert suite_response.status_code == 200
        eval_suite_id = suite_response.json()["eval_suite_id"]

        eval_response = client.post(
            "/eval-runs",
            json={
                "eval_suite_id": eval_suite_id,
                "model_version_id": model_version_id,
                "outputs": [
                    {
                        "eval_case_id": 1,
                        "prompt_text": "Explain binary search.",
                        "output_text": "Binary search is fast but this answer is too shallow.",
                        "scores": {
                            "coverage": 1.0,
                            "depth": 0.2,
                            "examples": 0.0,
                            "accuracy": 0.5,
                            "learning_flow": 0.0,
                            "overall": 0.34,
                        },
                        "failures": [
                            {
                                "failure_type": "shallow_explanation",
                                "severity": "high",
                                "failure_reason": "Missing depth and examples.",
                            }
                        ],
                    }
                ],
            },
        )
        assert eval_response.status_code == 200
        eval_run_id = eval_response.json()["eval_run_id"]
        assert eval_response.json()["failure_count"] == 1

        eval_detail = client.get(f"/eval-runs/{eval_run_id}").json()
        failure_id = eval_detail["failures"][0]["eval_failure_id"]
        summary = client.get("/evaluations/summary", params={"experiment_id": 1}).json()
        assert summary["eval_run_count"] == 1
        assert summary["output_count"] == 1
        assert summary["failure_count"] == 1
        assert summary["runs"][0]["score_summary"]["depth"]["mean"] == 0.2
        assert summary["runs"][0]["lineage_summary"]["model_version_id"] == model_version_id

        experiment_summary = client.get("/experiments/1/evaluation-summary").json()
        assert experiment_summary["metric_summary"][0]["metric_name"] == "accuracy"

        model_comparison = client.post(
            "/models/compare",
            json={
                "model_version_ids": [model_version_id],
                "baseline_model_version_id": model_version_id,
                "experiment_id": 1,
            },
        ).json()
        assert model_comparison["items"][0]["score_summary"]["overall"] == 0.34
        assert model_comparison["items"][0]["delta_from_baseline"]["overall"] == 0.0

        model_evals = client.get(f"/models/{model_version_id}/evals").json()
        assert model_evals["summary"]["eval_run_count"] == 1

        candidate_response = client.post(
            f"/eval-failures/{failure_id}/dataset-candidate",
            json={
                "target_dataset_id": 1,
                "proposed_input_text": "Revise the binary search guide.",
                "proposed_target_text": "A corrected guide should include definition, complexity, and examples.",
            },
        )
        assert candidate_response.status_code == 200
        candidate = candidate_response.json()
        assert candidate["eval_failure_id"] == failure_id
        assert candidate["source_eval_run_id"] == eval_run_id
        assert candidate["source_model_version_id"] == model_version_id
        candidate_id = candidate["dataset_candidate_id"]

        failures = client.get(
            "/failure-library",
            params={"experiment_id": 1, "failure_type": "shallow_explanation"},
        ).json()["items"]
        assert failures[0]["eval_failure_id"] == failure_id
        assert failures[0]["dataset_candidate_count"] == 1

        failure_detail = client.get(f"/failure-library/{failure_id}").json()
        assert failure_detail["lineage"][-1]["target_type"] == "eval_failure"
        assert failure_detail["dataset_candidates"][0]["dataset_candidate_id"] == candidate["dataset_candidate_id"]

        failure_summary = client.get("/failure-library/summary", params={"experiment_id": 1}).json()
        assert failure_summary["failure_count"] == 1
        assert failure_summary["by_failure_type"][0] == {"value": "shallow_explanation", "count": 1}

        candidates = client.get(
            "/dataset-candidates",
            params={
                "experiment_id": 1,
                "target_dataset_id": 1,
                "failure_type": "shallow_explanation",
            },
        ).json()["items"]
        assert candidates[0]["failure_type"] == "shallow_explanation"
        assert candidates[0]["target_dataset_id"] == 1

        review_response = client.patch(
            f"/dataset-candidates/{candidate_id}",
            json={
                "status": "approved",
                "review_notes": "Use this as a corrected study-guide training example.",
                "reviewed_by_user_id": "Lena Keys",
            },
        )
        assert review_response.status_code == 200
        reviewed_candidate = review_response.json()
        assert reviewed_candidate["status"] == "approved"
        assert reviewed_candidate["reviewed_by_user_id"] == "Lena Keys"

        iterations = client.get(
            "/dataset-iterations",
            params={"experiment_id": 1, "target_dataset_id": 1, "status": "approved"},
        ).json()["items"]
        assert iterations[0]["candidate_count"] == 1
        assert iterations[0]["included_count"] == 0

        version_response = client.post(
            "/datasets/1/versions/from-candidates",
            json={
                "candidate_ids": [candidate_id],
                "version_notes": "Add approved eval failure correction.",
                "created_by_user_id": "Lena Keys",
            },
        )
        assert version_response.status_code == 200
        created_version = version_response.json()
        assert created_version["dataset_version"]["dataset_id"] == 1
        assert created_version["dataset_version"]["dataset_version_id"] == 2
        assert created_version["candidate_count"] == 1
        assert created_version["included_candidate_ids"] == [candidate_id]
        assert created_version["iteration_manifest"]["parent_dataset_version_id"] == 1

        version_records = client.get("/datasets/1/versions/2/records?limit=100").json()["items"]
        assert len(version_records) == 41
        assert any(
            record["target_text"] == "A corrected guide should include definition, complexity, and examples."
            for record in version_records
        )

        included_candidate = client.get(f"/dataset-candidates/{candidate_id}").json()
        assert included_candidate["included_dataset_id"] == 1
        assert included_candidate["included_dataset_version_id"] == 2

        handoff = client.get("/datasets/1/versions/2/experiment-handoff").json()
        assert handoff["dataset_version"]["dataset_id"] == 1
        assert handoff["dataset_version"]["dataset_version_id"] == 2
        assert handoff["dataset_version"]["parent_dataset_version_id"] == 1
        assert handoff["failure_summary"]["candidate_count"] == 1
        assert handoff["failure_summary"]["source_eval_failure_ids"] == [failure_id]
        assert handoff["failure_summary"]["by_failure_type"] == [
            {"value": "shallow_explanation", "count": 1}
        ]
        assert handoff["source_candidates"][0]["dataset_candidate_id"] == candidate_id
        assert handoff["source_candidates"][0]["failure_reason"] == "Missing depth and examples."
        assert handoff["recommended_next_experiment"]["ready"] is True
        assert handoff["recommended_next_experiment"]["linked_datasets"] == [
            {"dataset_id": 1, "dataset_version_id": 2}
        ]

        accepted_handoff = client.post(
            "/experiments/1/dataset-handoffs",
            json={
                "dataset_id": 1,
                "dataset_version_id": 2,
                "updated_by_user_id": "Lena Keys",
            },
        ).json()
        assert accepted_handoff["accepted_dataset"] == {"dataset_id": 1, "dataset_version_id": 2}
        assert accepted_handoff["handoff"]["failure_summary"]["candidate_count"] == 1
        assert accepted_handoff["next_actions"] == [
            "launch_training_run_with_linked_dataset_version",
            "register_checkpoint_as_model_version",
            "rerun_source_eval_suite",
            "compare_new_model_to_source_model_versions",
        ]
        assert accepted_handoff["experiment"]["linked_datasets"] == [
            {"dataset_id": 1, "dataset_version_id": 1},
            {"dataset_id": 1, "dataset_version_id": 2},
        ]
        assert accepted_handoff["experiment"]["notes"][-1]["body"].startswith(
            "Accepted failure-replay dataset version 1.2"
        )

        next_run_plan = client.get("/experiments/1/next-run-plan").json()
        assert next_run_plan["can_register_run"] is True
        assert next_run_plan["selected_dataset"] == {"dataset_id": 1, "dataset_version_id": 2}
        assert next_run_plan["run_registration_payload"]["experiment_id"] == 1
        assert next_run_plan["run_registration_payload"]["dataset_version_id"] == 2
        assert next_run_plan["run_registration_payload"]["run_config"]["source"] == (
            "experiment_next_run_plan"
        )
        assert next_run_plan["next_actions"][0] == "POST /runs/register"

        included_iterations = client.get(
            "/dataset-iterations",
            params={"experiment_id": 1, "target_dataset_id": 1, "status": "approved"},
        ).json()["items"]
        assert included_iterations[0]["included_count"] == 1
    finally:
        app.dependency_overrides.clear()
