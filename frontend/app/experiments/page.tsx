import { LifecyclePage } from "../lifecycle-page";

export default function ExperimentsPage() {
  return (
    <LifecyclePage
      eyebrow="Experiments"
      title="Experiments"
      description="Track the research question and planned metric movement before looking at individual training jobs."
      status="Experiments sit between a hypothesis and one or more training runs. They should link to a data mixture, a training config, and comparison variants."
      cards={[
        {
          label: "seed example",
          title: "SFT baseline vs SFT + tool traces",
          body: "Compare a baseline instruction mixture against a 20 percent tool-use trace mixture.",
        },
        {
          title: "Expected metric movement",
          body: "State what should improve and which safety or regression metrics must not worsen.",
        },
        {
          title: "Variants",
          body: "Attach multiple data mixtures or training configs to one research question.",
        },
        {
          title: "Next decision",
          body: "Promote, rerun, change mixture, or convert failures into new data candidates.",
        },
      ]}
      apiRoutes={[
        "GET /experiments",
        "POST /experiments",
        "GET /experiments/{experiment_id}",
        "POST /experiments/{experiment_id}/variants",
      ]}
    />
  );
}
