import { LifecyclePage } from "../lifecycle-page";

export default function EvaluationsPage() {
  return (
    <LifecyclePage
      eyebrow="Evaluations"
      title="Evaluations"
      description="Answer whether a model version is actually better, worse, or newly risky."
      status="Evaluation runs should attach to model_version_id and write comparable scores, outputs, and failure cases."
      primaryHref="/models-checkpoints"
      primaryLabel="Open model registry"
      cards={[
        {
          title: "Eval suites",
          body: "Coverage, depth, example quality, learning progression, coding accuracy, safety, and regression evals.",
        },
        {
          title: "Model comparison",
          body: "Compare model versions only when eval-suite versions match.",
        },
        {
          title: "Regression indicators",
          body: "Surface newly introduced, fixed, and repeated failures.",
        },
        {
          title: "Failure handoff",
          body: "Send failed examples into the Failure Library with source model and dataset lineage.",
        },
      ]}
      apiRoutes={[
        "GET /eval-suites",
        "POST /eval-suites",
        "POST /eval-runs",
        "GET /eval-runs/{eval_run_id}",
        "GET /model-versions/{model_version_id}/eval-summary",
      ]}
    />
  );
}
