from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.research_programs.api import (
    get_research_program_repository,
    get_research_program_storage_root,
)
from app.research_programs.repository import ResearchProgramRepository


def test_research_programs_can_be_registered_and_updated_for_ui(tmp_path: Path) -> None:
    duckdb_path = tmp_path / "duckdb" / "research_command_center.duckdb"

    def override_repository() -> ResearchProgramRepository:
        return ResearchProgramRepository(duckdb_path=duckdb_path, storage_root=tmp_path)

    app.dependency_overrides[get_research_program_repository] = override_repository
    app.dependency_overrides[get_research_program_storage_root] = lambda: tmp_path
    try:
        client = TestClient(app)
        create_response = client.post(
            "/research-programs",
            json={
                "program_name": "Improve structured technical study-material generation",
                "short_name": "Python algorithms study guides",
                "program_description": "Improve long-form educational artifacts for technical learners.",
                "problem_statement": "Generated Python algorithm study guides are shallow and uneven.",
                "origin_story": "A user asked for Python algorithms study materials and received a weak final document.",
                "research_goal": "Improve coverage, depth, examples, ordering, and usefulness.",
                "hypothesis": "Structured examples and corrected failures improve long-form study guides.",
                "target_outcome": "A model that can produce a complete study guide from a simple request.",
                "status": "active",
                "research_area": "model_behavior",
                "current_focus": "Build the first rubric-backed evaluation slice.",
                "owner_name": "minion1",
                "researcher_names": ["minion1", "minion2"],
                "success_metrics": ["coverage_score", "depth_score", "example_quality_score"],
                "tags": ["study_material", "python_algorithms", "long_form_generation"],
                "linked_dataset_ids": [1],
                "decision_notes": "Seeded from the owner experience for the first demo program.",
            },
        )
        assert create_response.status_code == 200
        created = create_response.json()
        assert created["program_id"] == 1
        assert created["researcher_names"] == ["minion1", "minion2"]

        list_response = client.get("/research-programs", params={"status": "active"})
        assert list_response.status_code == 200
        assert list_response.json()["items"][0]["program_id"] == 1

        detail_response = client.get("/research-programs/1")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["program_name"] == "Improve structured technical study-material generation"
        assert detail["program_description"] == "Improve long-form educational artifacts for technical learners."
        assert detail["target_outcome"] == "A model that can produce a complete study guide from a simple request."
        assert detail["linked_dataset_ids"] == [1]
        assert detail["ui_workflow"]["can_update_from_ui"] is True

        patch_response = client.patch(
            "/research-programs/1",
            json={
                "status": "paused",
                "current_focus": "Waiting for evaluation-slice implementation.",
                "target_outcome": "Produce useful, complete study guides with measurable rubric gains.",
                "researcher_names": ["minion1", "minion2", "minion3"],
            },
        )
        assert patch_response.status_code == 200
        patched = patch_response.json()
        assert patched["status"] == "paused"
        assert patched["target_outcome"] == "Produce useful, complete study guides with measurable rubric gains."
        assert patched["researcher_names"] == ["minion1", "minion2", "minion3"]
    finally:
        app.dependency_overrides.clear()
