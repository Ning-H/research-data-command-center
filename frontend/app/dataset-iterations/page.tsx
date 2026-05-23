import { LifecyclePage } from "../lifecycle-page";

export default function DatasetIterationsPage() {
  return (
    <LifecyclePage
      eyebrow="Dataset Iterations"
      title="Dataset Iterations"
      description="Close the loop from model failures into new data candidates, approved dataset versions, and the next experiment."
      status="Dataset iterations should make it obvious which failures justified a new version and which future experiments consume it."
      primaryHref="/data-assets"
      primaryLabel="Open data assets"
      cards={[
        {
          title: "Review candidates",
          body: "Approve or reject examples produced from eval failures and inference traces.",
        },
        {
          title: "Create next version",
          body: "Build failure-derived dataset versions without mutating prior immutable versions.",
        },
        {
          title: "Governance",
          body: "Keep quality score, PII/safety review, source priority, and license context visible.",
        },
        {
          title: "Next experiment",
          body: "Link the new dataset version or mixture to the next research hypothesis.",
        },
      ]}
      apiRoutes={[
        "GET /dataset-candidates",
        "PATCH /dataset-candidates/{candidate_id}",
        "POST /data-assets/{asset_id}/versions/from-candidates",
      ]}
    />
  );
}
