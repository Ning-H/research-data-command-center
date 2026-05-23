import { LifecyclePage } from "../lifecycle-page";

export default function WorkspacePage() {
  return (
    <LifecyclePage
      eyebrow="Workspace"
      title="Workspace"
      description="A researcher review queue for notes, approvals, candidate examples, and follow-up decisions."
      status="Workspace is not a separate data silo; it is a workbench over programs, failures, dataset candidates, and model readiness decisions."
      cards={[
        {
          title: "Review queue",
          body: "Dataset candidates, severe failures, model promotion decisions, and eval regressions.",
        },
        {
          title: "Notes",
          body: "Human research notes attached to durable lineage entities.",
        },
        {
          title: "Approvals",
          body: "Approve dataset versions, promotion candidates, and demo-ready model versions.",
        },
        {
          title: "Next actions",
          body: "Create experiment, rerun training, run eval, or create a dataset candidate.",
        },
      ]}
      apiRoutes={["GET /workspace/review-queue", "POST /workspace/notes", "PATCH /workspace/decisions/{decision_id}"]}
    />
  );
}
