import { LifecyclePage } from "../lifecycle-page";

export default function ResearchProgramsPage() {
  return (
    <LifecyclePage
      eyebrow="Research Programs"
      title="Research Programs"
      description="Group hypotheses, experiments, runs, evals, failures, and dataset iterations around a research goal."
      status="This becomes the top-level container for work like improving structured technical documents, reducing hallucination, or improving harmlessness without over-refusal."
      cards={[
        {
          label: "seed example",
          title: "Improve study-material generation",
          body: "Track whether structured examples and corrected failures improve Python algorithms study guides.",
        },
        {
          title: "Hypotheses",
          body: "Attach measurable research claims before the team inspects run metrics.",
        },
        {
          title: "Program status",
          body: "Planning, active, paused, completed, with linked data assets, experiments, and model versions.",
        },
        {
          title: "Decision history",
          body: "Keep why a dataset or checkpoint was chosen next to the lineage graph.",
        },
      ]}
      apiRoutes={[
        "GET /research-programs",
        "POST /research-programs",
        "GET /research-programs/{program_id}",
        "POST /research-programs/{program_id}/hypotheses",
      ]}
    />
  );
}
