import { LifecyclePage } from "../lifecycle-page";

export default function InferenceObservabilityPage() {
  return (
    <LifecyclePage
      eyebrow="Inference Observability"
      title="Inference Observability"
      description="Track real or scripted model generations after deployment, including prompts, responses, latency, token usage, retrieval context, and safety filters."
      status="This page makes the project feel closer to production AI behavior while still keeping the platform focused on research data."
      cards={[
        {
          title: "Inference traces",
          body: "Prompt, generated study guide, token counts, latency, model_version_id, and deployment context.",
        },
        {
          title: "Document traces",
          body: "Track requested topic list, outline shape, generated sections, source context, and reviewer feedback.",
        },
        {
          title: "Safety results",
          body: "Record filter decisions, refusal behavior, and user feedback.",
        },
        {
          title: "Failure conversion",
          body: "Convert bad traces into failure cases and later dataset candidates.",
        },
      ]}
      apiRoutes={[
        "GET /inference-traces",
        "POST /inference-traces",
        "GET /inference-traces/{trace_id}",
        "GET /inference-traces/summary",
        "POST /inference-traces/{trace_id}/failure-case",
      ]}
    />
  );
}
