import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getRun } from "../../../lib/api";

type RunDetailPageProps = {
  params: {
    runId: string;
  };
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  let run;
  try {
    run = await getRun(params.runId);
  } catch {
    notFound();
  }
  const checkpointSearchHref = `/runs/checkpoints?${new URLSearchParams({
    dataset_id: String(run.dataset_id),
    dataset_version_id: String(run.dataset_version_id),
    framework: String(run.run_config.config.framework ?? ""),
    trainer: String(run.run_config.config.trainer ?? ""),
    ranking_metric: "train.accuracy",
    direction: "desc",
  }).toString()}`;

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Run Detail</p>
          <h1>{run.run_name}</h1>
          <p className="subtle">
            Researcher-submitted run data normalized into metrics, checkpoint metadata, health,
            and lineage. Training and checkpoint file creation happened outside this platform.
          </p>
        </div>
        <Link className="button secondary" href="/training-runs">
          <ArrowLeft aria-hidden="true" size={16} />
          Training Runs
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Status</p>
          <p className="metric-value compact">{run.status}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Health</p>
          <p className="metric-value">{run.health_summary.health_score}/100</p>
          <p className="metric-label">{run.health_summary.health_label}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Final loss</p>
          <p className="metric-value">{formatMetric(run.metric_summary.final_loss)}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Checkpoints</p>
          <p className="metric-value">{run.checkpoint_count}</p>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Run Source & Config</h2>
          <p className="subtle">{run.raw_ingest_summary.note}</p>
        </div>
        <div className="metadata-grid">
          <Metadata label="run_id" value={run.run_id} />
          <Metadata label="run_config_id" value={run.run_config_id} />
          <Metadata label="dataset_id" value={run.dataset_id} />
          <Metadata label="dataset_version_id" value={run.dataset_version_id} />
          <Metadata label="model_family" value={run.model_family} />
          <Metadata label="training_environment" value={run.training_environment} />
          <Metadata label="framework" value={String(run.run_config.config.framework ?? "not provided")} />
          <Metadata label="tracker" value={String(run.run_config.config.tracker ?? "not provided")} />
          <Metadata label="device" value={String(run.run_config.config.device ?? "not provided")} />
          <Metadata label="trainer" value={String(run.run_config.config.trainer ?? "not provided")} />
          <Metadata label="ingest_source" value={run.ingest_source} />
          <Metadata label="raw_events_uri" value={run.raw_events_uri} />
          <Metadata label="started_at" value={formatDateTime(run.started_at)} />
          <Metadata label="ended_at" value={run.ended_at ? formatDateTime(run.ended_at) : "not completed"} />
          <Metadata label="source_priority" value={run.source_priority} />
          <Metadata label="model_version_status" value={run.model_version_status} />
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Training Metrics</h2>
            <p className="subtle">Long-format metrics normalized from raw researcher-submitted events.</p>
          </div>
          <div className="component-grid">
            <MetricCard label="initial_loss" value={formatMetric(run.metric_summary.initial_loss)} />
            <MetricCard label="final_loss" value={formatMetric(run.metric_summary.final_loss)} />
            <MetricCard label="loss_delta" value={`${run.metric_summary.loss_delta_percent}%`} />
            <MetricCard label="tokens_seen" value={run.metric_summary.tokens_seen.toLocaleString()} />
          </div>
          <div className="sparkline">
            {run.metric_series.map((point) => (
              <span
                key={point.step}
                style={{ height: `${Math.max(8, Math.min(96, point.metric_value * 26))}px` }}
                title={`step ${point.step}: ${formatMetric(point.metric_value)}`}
              />
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Compute Summary</h2>
            <p className="subtle">Physics-constrained demo telemetry derived from the raw run timeline.</p>
          </div>
          <div className="metadata-grid">
            <Metadata label="avg_gpu_utilization" value={`${run.compute_summary.avg_gpu_utilization}%`} />
            <Metadata label="max_memory_used_gb" value={run.compute_summary.max_memory_used_gb} />
            <Metadata label="avg_process_memory_mb" value={run.compute_summary.avg_process_memory_mb} />
            <Metadata label="avg_tokens_per_second" value={run.compute_summary.avg_tokens_per_second} />
            <Metadata label="estimated_cost_usd" value={`$${run.compute_summary.estimated_cost_usd}`} />
          </div>
          <div className="quality-note">
            <span className={run.status === "failed" ? "badge warning" : "badge"}>
              {run.health_summary.health_label}
            </span>
            <p>{run.compute_summary.hardware_note}</p>
            <p>{run.health_summary.signals.join(" · ")}</p>
          </div>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Checkpoints</h2>
            <p className="subtle">
              Checkpoint files were saved by the training job; this platform stores their URI,
              step, metrics snapshot, and promotion-ready lineage.
            </p>
            <Link className="button secondary" href={checkpointSearchHref}>
              Compare same dataset / trainer
              <ArrowRight aria-hidden="true" size={16} />
            </Link>
          </div>
          <div className="record-list">
            {run.checkpoints.map((checkpoint) => (
              <article className="record" key={checkpoint.checkpoint_id}>
                <span className="badge">{checkpoint.status}</span>
                <h3>checkpoint_id {checkpoint.checkpoint_id}</h3>
                <Metadata label="step" value={checkpoint.step} />
                <Metadata label="checkpoint_uri" value={checkpoint.checkpoint_uri} />
                <Metadata label="train.loss" value={formatMetric(checkpoint.metrics_snapshot["train.loss"])} />
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Lineage</h2>
            <p className="subtle">The run is the bridge from dataset version to checkpoint and later model version.</p>
          </div>
          <div className="record-list">
            {run.lineage.map((edge) => (
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

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="component-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
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
    return "0";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
}

function formatDateTime(value: string) {
  return value.replace("T", " ").replace("Z", " UTC");
}
