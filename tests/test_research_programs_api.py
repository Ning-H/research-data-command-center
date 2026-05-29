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
                "program_description": "Improve long-form educational artifacts for technical learners.",
                "problem_statement": "Generated Python algorithm study guides are shallow and uneven.",
                "initiating_context": "A user asked for Python algorithms study materials and received a weak final document.",
                "research_goal": "Improve coverage, depth, examples, ordering, and usefulness.",
                "hypothesis": "Structured examples and corrected failures improve long-form study guides.",
                "research_objectives": "Learn which data and eval recipe improves study guide quality.",
                "status": "active",
                "research_area": "model_behavior",
                "current_focus": "Build the first rubric-backed evaluation slice.",
                "owner_name": "minion1",
                "researcher_names": ["minion1", "minion2"],
                "tags": ["study_material", "python_algorithms", "long_form_generation"],
                "linked_datasets": [{"dataset_id": 1, "dataset_version_id": 1}],
                "linked_experiment_ids": [1],
                "linked_run_ids": [7],
                "notes": [
                    {
                        "body": "Seeded from the owner experience for the first demo program.",
                        "author_name": "minion1",
                    }
                ],
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
        assert "short_name" not in detail
        assert detail["program_description"] == "Improve long-form educational artifacts for technical learners."
        assert detail["initiating_context"] == "A user asked for Python algorithms study materials and received a weak final document."
        assert detail["research_objectives"] == "Learn which data and eval recipe improves study guide quality."
        assert detail["linked_datasets"] == [{"dataset_id": 1, "dataset_version_id": 1}]
        assert detail["linked_experiment_ids"] == [1]
        assert detail["linked_run_ids"] == [7]
        assert detail["notes"][0]["body"] == "Seeded from the owner experience for the first demo program."
        assert "decision_notes" not in detail
        assert detail["ui_workflow"]["can_update_from_ui"] is True
        assert "attach_training_runs" in detail["ui_workflow"]["supported_actions"]
        assert "append_note" in detail["ui_workflow"]["supported_actions"]
        assert "success_metrics" not in detail
        assert all(not key.endswith("_json") for key in detail)

        tag_response = client.get("/research-programs", params={"tag": "python_algorithms"})
        assert tag_response.status_code == 200
        assert tag_response.json()["items"][0]["program_id"] == 1

        search_response = client.get("/research-programs", params={"q": "study guide"})
        assert search_response.status_code == 200
        assert search_response.json()["items"][0]["program_id"] == 1

        patch_response = client.patch(
            "/research-programs/1",
            json={
                "status": "paused",
                "current_focus": "Waiting for evaluation-slice implementation.",
                "research_objectives": "Measure whether structured data improves study guide quality.",
                "researcher_names": ["minion1", "minion2", "minion3"],
            },
        )
        assert patch_response.status_code == 200
        patched = patch_response.json()
        assert patched["status"] == "paused"
        assert patched["research_objectives"] == "Measure whether structured data improves study guide quality."
        assert patched["researcher_names"] == ["minion1", "minion2", "minion3"]

        note_response = client.post(
            "/research-programs/1/notes",
            json={"body": "Keep the first evaluation slice narrow.", "author_name": "minion2"},
        )
        assert note_response.status_code == 200
        note_payload = note_response.json()
        assert note_payload["note_id"] == 2
        assert note_payload["notes"][1]["author_name"] == "minion2"
        assert note_payload["program"]["notes"][1]["body"] == "Keep the first evaluation slice narrow."
        assert "delete_note" in note_payload["program"]["ui_workflow"]["supported_actions"]

        delete_response = client.request(
            "DELETE",
            "/research-programs/1/notes/1",
            json={"user_id": "minion2"},
        )
        assert delete_response.status_code == 200
        delete_payload = delete_response.json()
        assert delete_payload["deleted_note_id"] == 1
        assert [note["note_id"] for note in delete_payload["notes"]] == [2]
        assert delete_payload["program"]["notes"][0]["body"] == "Keep the first evaluation slice narrow."

        missing_note_response = client.request("DELETE", "/research-programs/1/notes/99")
        assert missing_note_response.status_code == 404
        assert "note_id 99 does not exist" in missing_note_response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
