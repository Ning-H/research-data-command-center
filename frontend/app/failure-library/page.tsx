import { LifecyclePage } from "../lifecycle-page";

export default function FailureLibraryPage() {
  return (
    <LifecyclePage
      eyebrow="Failure Library"
      title="Failure Library"
      description="Centralize model failures from evals and inference traces, then route them into dataset iteration."
      status="This is where hallucinations, unsafe outputs, over-refusals, tool-use failures, retrieval failures, and formatting issues become actionable research data."
      cards={[
        {
          title: "Failure types",
          body: "Hallucination, bad reasoning, bad code, unsafe output, over-refusal, tool-use failure, retrieval failure, long-context failure, and latency failure.",
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
