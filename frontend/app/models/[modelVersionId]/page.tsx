import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getModel } from "../../../lib/api";

type ModelDetailPageProps = {
  params: {
    modelVersionId: string;
  };
};

export default async function ModelDetailPage({ params }: ModelDetailPageProps) {
  let model;
  try {
    model = await getModel(params.modelVersionId);
  } catch {
    notFound();
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Model Detail</p>
          <h1>{model.model_version_name}</h1>
          <p className="subtle">
            Immutable candidate model version registered from checkpoint_id {model.checkpoint_id}.
            Evaluation and comparison results will attach here next.
          </p>
        </div>
        <Link className="button secondary" href="/models">
          <ArrowLeft aria-hidden="true" size={16} />
          Models
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Status</p>
          <p className="metric-value compact">{model.status}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Model version</p>
          <p className="metric-value">{model.model_version_id}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Source checkpoint</p>
          <p className="metric-value">{model.checkpoint_id}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Run</p>
          <p className="metric-value">{model.run_id}</p>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Model Version Metadata</h2>
          <p className="subtle">
            The researcher provides model intent and naming; lineage fields are derived from the
            checkpoint and run records.
          </p>
        </div>
        <div className="metadata-grid">
          <Metadata label="model_id" value={model.model_id} />
          <Metadata label="model_version_id" value={model.model_version_id} />
          <Metadata label="model_name" value={model.model_name} />
          <Metadata label="checkpoint_id" value={model.checkpoint_id} />
          <Metadata label="run_id" value={model.run_id} />
          <Metadata label="dataset_id" value={model.dataset_id} />
          <Metadata label="dataset_version_id" value={model.dataset_version_id} />
          <Metadata label="source_checkpoint_step" value={model.source_checkpoint_step} />
          <Metadata label="created_by_user_id" value={model.created_by_user_id} />
          <Metadata label="created_at" value={formatDateTime(model.created_at)} />
          <Metadata label="source_priority" value={model.source_priority} />
          <Metadata label="artifact_uri" value={model.artifact_uri} />
        </div>
        <div className="description-box">
          <span>intended_use</span>
          <p>{model.intended_use || "Not provided."}</p>
        </div>
        <div className="description-box">
          <span>promotion_reason</span>
          <p>{model.promotion_reason || "Not provided."}</p>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Checkpoint Metrics Snapshot</h2>
            <p className="subtle">Metrics captured at the source checkpoint promotion point.</p>
          </div>
          <div className="metadata-grid">
            {Object.entries(model.metrics_snapshot).map(([metricName, metricValue]) => (
              <Metadata key={metricName} label={metricName} value={formatMetric(metricValue)} />
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Lineage</h2>
            <p className="subtle">Model lineage is derived, not manually reconstructed.</p>
          </div>
          <div className="record-list">
            {model.lineage.map((edge) => (
              <article className="record" key={`${edge.lineage_step}-${edge.target_id}`}>
                <span className="badge neutral">{edge.lineage_step}</span>
                <Metadata label="source" value={`${edge.source_type}:${edge.source_id}`} />
                <Metadata label="target" value={`${edge.target_type}:${edge.target_id}`} />
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

function Metadata({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatMetric(value: number | undefined) {
  if (value === undefined) {
    return "not logged";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
}

function formatDateTime(value: string) {
  return value.replace("T", " ").replace("Z", " UTC");
}
