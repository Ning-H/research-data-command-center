from pathlib import Path

from fastapi.testclient import TestClient

from app.experiments.api import get_experiment_repository, get_experiment_storage_root
from app.experiments.repository import ExperimentRepository
from app.main import app
from app.research_programs.lifecycle import register_research_program
from app.research_programs.repository import ResearchProgramRepository


def test_experiments_can_be_registered_under_research_programs(tmp_path: Path) -> None:
    duckdb_path = tmp_path / "duckdb" / "research_command_center.duckdb"
    register_research_program(
        storage_root=tmp_path,
        payload={
            "program_name": "Improve structured technical study-material generation",
            "short_name": "Python algorithms study guides",
            "status": "active",
            "owner_name": "Lena Keys",
            "researcher_names": ["Lena Keys", "Miles Drums"],
            "tags": ["technical_education"],
        },
    )

    def override_repository() -> ExperimentRepository:
        return ExperimentRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    app.dependency_overrides[get_experiment_repository] = override_repository
    app.dependency_overrides[get_experiment_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        create_response = client.post(
            "/experiments",
            json={
                "program_id": 1,
                "experiment_name": "Outline-first algorithm study-guide data recipe",
                "experiment_description": (
                    "Compare direct-answer examples against outline-first study-guide examples."
                ),
                "research_question": (
                    "Does outline-first supervision improve completeness and learning flow?"
                ),
                "hypothesis": (
                    "Structured exemplars and corrected failures improve long-form study guides."
                ),
                "experiment_type": "data_recipe_ablation",
                "status": "planning",
                "owner_name": "Lena Keys",
                "current_focus": "Prepare data assets and rubric-labeled eval cases.",
                "data_strategy": "Use public coding/QA records plus generated study-guide examples.",
                "evaluation_plan": "Score coverage, depth, example relevance, and factual accuracy.",
                "tags": ["python_algorithms", "study_material"],
                "variants": [
                    {
                        "variant_name": "baseline_direct_answer",
                        "description": "Use existing instruction-tuning data only.",
                        "data_recipe": "100% baseline instruction data",
                    },
                    {
                        "variant_name": "outline_first_guides",
                        "description": "Add structured algorithm guide exemplars.",
                        "data_recipe": "80% baseline + 20% outline-first study-guide data",
                    },
                ],
                "linked_datasets": [{"dataset_id": 1, "dataset_version_id": 1}],
                "decision_notes": "First experiment under the program.",
            },
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["experiment_id"] == 1
        assert created["program_id"] == 1

        detail_response = client.get("/experiments/1")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["program_id"] == 1
        assert detail["experiment_name"] == "Outline-first algorithm study-guide data recipe"
        assert detail["research_question"].startswith("Does outline-first")
        assert detail["linked_datasets"] == [{"dataset_id": 1, "dataset_version_id": 1}]
        assert detail["variants"][1]["variant_name"] == "outline_first_guides"
        assert detail["ui_workflow"]["can_update_from_ui"] is True
        assert "attach_training_runs" in detail["ui_workflow"]["supported_actions"]
        assert all(not key.endswith("_json") for key in detail)

        list_response = client.get("/experiments", params={"program_id": 1, "tag": "study_material"})
        assert list_response.status_code == 200
        assert list_response.json()["items"][0]["experiment_id"] == 1

        search_response = client.get("/experiments", params={"q": "rubric-labeled"})
        assert search_response.status_code == 200
        assert search_response.json()["items"][0]["experiment_id"] == 1

        patch_response = client.patch(
            "/experiments/1",
            json={
                "status": "active",
                "linked_run_ids": [7],
                "decision_notes": "Approved for the first externally reported training run.",
            },
        )
        assert patch_response.status_code == 200
        patched = patch_response.json()
        assert patched["status"] == "active"
        assert patched["linked_run_ids"] == [7]

        program = ResearchProgramRepository(duckdb_path=duckdb_path, storage_root=tmp_path).get_program(1)
        assert program is not None
        assert program["linked_datasets"] == [{"dataset_id": 1, "dataset_version_id": 1}]
        assert program["linked_experiment_ids"] == [1]
        assert program["linked_run_ids"] == [7]
    finally:
        app.dependency_overrides.clear()
