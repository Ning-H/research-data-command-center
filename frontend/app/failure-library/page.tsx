import { LifecyclePage } from "../lifecycle-page";

export default function FailureLibraryPage() {
  return (
    <LifecyclePage
      eyebrow="Failure Library"
      title="Failure Library"
      description="Centralize model failures from evals and inference traces, then route them into dataset iteration."
      status="This is where shallow explanations, missing topics, inaccurate code, hallucinations, unsafe outputs, and formatting issues become actionable research data."
      cards={[
        {
          title: "Failure types",
          body: "Missing algorithm category, shallow explanation, no code pattern, no practice example, bad complexity analysis, hallucination, and format failure.",
        },
        {
          title: "Severity workflow",
          body: "Assign severity, review status, owner, and root-cause notes.",
        },
        {
          title: "Lineage context",
          body: "Keep model_version_id, checkpoint_id, run_id, dataset_version_id, and eval_run_id visible.",
        },
        {
          title: "Dataset candidate",
          body: "Turn reviewed failures into candidate examples for the next data version.",
        },
      ]}
      apiRoutes={[
        "GET /failure-cases",
        "POST /failure-cases",
        "GET /failure-cases/{failure_id}",
        "PATCH /failure-cases/{failure_id}",
        "POST /failure-cases/{failure_id}/dataset-candidate",
      ]}
    />
  );
}
