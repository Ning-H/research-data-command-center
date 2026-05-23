import { LifecyclePage } from "../lifecycle-page";

export default function SettingsPage() {
  return (
    <LifecyclePage
      eyebrow="Settings"
      title="Settings"
      description="Configuration for local storage, data source labels, model registry defaults, and demo seed behavior."
      status="Settings stays intentionally narrow for v1. Auth, permissions, S3, Spark, and hosted deployments are later-phase work."
      cards={[
        {
          title: "Storage layers",
          body: "Parquet + DuckDB for analytical data, Postgres for app metadata, object-store folders for raw artifacts.",
        },
        {
          title: "Source priority",
          body: "PUBLIC_REAL, GENERATED_REAL, and SYNTHETIC_REALISTIC labels remain required.",
        },
        {
          title: "Version rules",
          body: "Dataset versions, model versions, and eval-suite versions are immutable once created.",
        },
        {
          title: "Later infra",
          body: "Spark, S3, auth, permissions, and streaming ingestion stay out of the v1 critical path.",
        },
      ]}
      apiRoutes={["GET /contract", "GET /health"]}
    />
  );
}
