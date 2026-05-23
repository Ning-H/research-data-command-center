import { LifecyclePage } from "../lifecycle-page";

export default function DocsPage() {
  return (
    <LifecyclePage
      eyebrow="Docs"
      title="Docs"
      description="API, SDK, data dictionary, lineage model, and demo-flow documentation for the portfolio project."
      status="Docs should explain the product story and give reviewers concrete API/SDK examples they can inspect."
      cards={[
        {
          title: "Data dictionary",
          body: "Canonical IDs, core tables, source-priority labels, and immutable version rules.",
        },
        {
          title: "API reference",
          body: "Research programs, data assets, runs, checkpoints, models, evals, failures, and dataset candidates.",
        },
        {
          title: "SDK examples",
          body: "Register data, register run, append metrics, promote checkpoint, run eval, create candidate.",
        },
        {
          title: "Demo script",
          body: "Tool-use reliability story from hypothesis to next dataset iteration.",
        },
      ]}
      apiRoutes={["GET /contract", "GET /health"]}
    />
  );
}
