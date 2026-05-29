import { ArrowLeft, Boxes, Cpu, GitBranch, LineChart } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import type { RunCheckpoint, RunComputeMetric, RunMetric } from "../../../lib/api";
import { getRun, getRunComputeMetrics, getRunMetrics } from "../../../lib/api";
import CheckpointCompare from "./CheckpointCompare";

type RunDetailPageProps = {
  params: {
    runId: string;
  };
};

type MetricSeries = {
  name: string;
  points: RunMetric[];
};

export default async function RunDetailPage({ params }: RunDetailPageProps) {
  let run;
  let metrics: RunMetric[];
  let computeMetrics: RunComputeMetric[];
  try {
    [run, metrics, computeMetrics] = await Promise.all([
      getRun(params.runId),
      getRunMetrics(params.runId),
      getRunComputeMetrics(params.runId),
    ]);
  } catch {
    notFound();
  }

  const groupedMetrics = priorityMetricSeries(groupMetrics(metrics));
  const groupedCompute = priorityMetricSeries(groupMetrics(computeMetrics));
  const bestCheckpoint = chooseBestCheckpoint(run.checkpoints);
  const configEntries = Object.entries(run.run_config.config ?? {});

  return (
    <section className="page run-detail-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Run Analysis</p>
          <h1>{run.run_name}</h1>
          <p className="subtle">
            Metrics, compute telemetry, checkpoints, and lineage submitted by an external trainer.
            This page is read-only analysis; the run was captured through the API/SDK.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/training-runs">
          <ArrowLeft aria-hidden="true" size={16} />
          Training Runs
        </Link>
      </div>

      <div className="summary-grid run-summary-grid">
        <MetricCard label="status" value={run.status} detail={formatDuration(run.started_at, run.ended_at)} />
        <MetricCard
          label="health"
          value={`${run.health_summary.health_score}/100`}
          detail={run.health_summary.health_label}
        />
        <MetricCard
          label="final loss"
          value={formatMetric(run.metric_summary.final_loss)}
          detail={`delta ${formatSignedPercent(run.metric_summary.loss_delta_percent)}`}
        />
        <MetricCard
          label="best checkpoint"
          value={bestCheckpoint ? `#${bestCheckpoint.checkpoint_id}` : "n/a"}
          detail={bestCheckpoint ? `step ${bestCheckpoint.step}` : "no checkpoints"}
        />
      </div>

      <div className="two-column runs-overview-grid">
        <div className="panel run-metric-panel">
          <div className="panel-heading-row">
            <div>
              <h2>Training Metric Analysis</h2>
              <p className="subtle">
                Generated from normalized metric rows. New metrics submitted by future trainers
                appear here without UI changes.
              </p>
            </div>
            <LineChart aria-hidden="true" className="accent-icon" size={20} />
          </div>
          {groupedMetrics.length ? (
            <div className="metric-chart-grid">
              {groupedMetrics.map((series) => (
                <MetricLineChart
                  checkpoints={run.checkpoints}
                  key={series.name}
                  series={series}
                />
              ))}
            </div>
          ) : (
            <EmptyState text="No training metric events were submitted for this run." />
          )}
        </div>

        <div className="panel run-decision-panel">
          <div className="panel-heading-row">
            <div>
              <h2>Outcome Summary</h2>
              <p className="subtle">Fast read of whether this run is useful, failed, or needs review.</p>
            </div>
            <Boxes aria-hidden="true" className="accent-icon" size={20} />
          </div>
          <div className="outcome-list">
            <OutcomeRow label="initial loss" value={formatMetric(run.metric_summary.initial_loss)} />
            <OutcomeRow label="final loss" value={formatMetric(run.metric_summary.final_loss)} />
            <OutcomeRow label="min loss" value={formatMetric(run.metric_summary.min_loss)} />
            <OutcomeRow label="loss delta" value={formatSignedPercent(run.metric_summary.loss_delta_percent)} />
            <OutcomeRow label="tokens seen" value={formatCount(run.metric_summary.tokens_seen)} />
            <OutcomeRow label="checkpoints" value={String(run.checkpoint_count)} />
          </div>
          <div className="quality-note">
            <span className={run.status === "failed" ? "badge warning" : run.status === "completed" ? "badge status-completed" : "badge"}>
              {run.health_summary.health_label}
            </span>
            <p>{run.health_summary.signals.join(" · ") || "No health signals were available."}</p>
          </div>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div className="panel-heading-row">
            <div>
              <h2>Compute Telemetry</h2>
              <p className="subtle">
                Process, throughput, cost, and hardware metrics submitted by the training environment.
              </p>
            </div>
            <Cpu aria-hidden="true" className="accent-icon" size={20} />
          </div>
          <div className="metadata-grid">
            <Metadata label="avg_gpu_utilization" value={formatMaybePercent(run.compute_summary.avg_gpu_utilization)} />
            <Metadata label="max_memory_used_gb" value={formatMaybeNumber(run.compute_summary.max_memory_used_gb)} />
            <Metadata label="avg_process_memory_mb" value={formatMaybeNumber(run.compute_summary.avg_process_memory_mb)} />
            <Metadata label="avg_tokens_per_second" value={formatMaybeNumber(run.compute_summary.avg_tokens_per_second)} />
            <Metadata label="estimated_cost_usd" value={`$${formatMaybeNumber(run.compute_summary.estimated_cost_usd)}`} />
          </div>
          {groupedCompute.length ? (
            <div className="compute-series-list">
              {groupedCompute.map((series) => (
                <ComputeMetricStrip key={series.name} series={series} />
              ))}
            </div>
          ) : (
            <EmptyState text={run.compute_summary.hardware_note ?? "No compute telemetry was submitted."} />
          )}
        </div>

        <div className="panel">
          <div>
            <h2>Run Source & Config</h2>
            <p className="subtle">{run.raw_ingest_summary.note}</p>
          </div>
          <div className="metadata-grid single-column">
            <Metadata label="run_id" value={run.run_id} />
            <Metadata label="program_id" value={run.program_id ?? "unlinked"} />
            <Metadata label="experiment_id" value={run.experiment_id ?? "unlinked"} />
            <Metadata label="dataset_version" value={`${run.dataset_id}/${run.dataset_version_id}`} />
            <Metadata label="model_family" value={run.model_family} />
            <Metadata label="training_environment" value={run.training_environment} />
            <Metadata label="ingest_source" value={run.ingest_source} />
            <Metadata label="started_at" value={formatDateTime(run.started_at)} />
            <Metadata label="ended_at" value={run.ended_at ? formatDateTime(run.ended_at) : "not completed"} />
            <Metadata label="raw_events_uri" value={run.raw_events_uri} />
          </div>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div className="panel-heading-row">
            <div>
              <h2>Checkpoints</h2>
              <p className="subtle">
                Artifact files remain in run-owned storage; this page analyzes checkpoint metadata
                and metric snapshots.
              </p>
            </div>
          </div>
          <CheckpointCompare bestCheckpointId={bestCheckpoint?.checkpoint_id} checkpoints={run.checkpoints} />
        </div>

        <div className="panel">
          <div className="panel-heading-row">
            <div>
              <h2>Lineage</h2>
              <p className="subtle">The run connects a governed dataset version to checkpoints and later model versions.</p>
            </div>
            <GitBranch aria-hidden="true" className="accent-icon" size={20} />
          </div>
          <LineageFlow lineage={run.lineage} />
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Config Snapshot</h2>
          <p className="subtle">
            Read-only parameters captured when the training job started.
          </p>
        </div>
        {configEntries.length ? (
          <div className="config-grid">
            {configEntries.map(([key, value]) => (
              <Metadata key={key} label={key} value={formatConfigValue(value)} />
            ))}
          </div>
        ) : (
          <EmptyState text="No run config values were submitted." />
        )}
      </div>
    </section>
  );
}

function MetricCard({ detail, label, value }: { detail: string; label: string; value: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value compact">{value}</p>
      <p className="metric-label">{detail}</p>
    </div>
  );
}

function MetricLineChart({ checkpoints, series }: { checkpoints: RunCheckpoint[]; series: MetricSeries }) {
  const points = sortedPoints(series.points);
  const values = points.map((point) => point.metric_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const first = values[0];
  const last = values[values.length - 1];
  const polyline = svgPolyline(points);
  const checkpointSteps = checkpoints.map((checkpoint) => checkpoint.step);

  return (
    <article className="metric-chart-card">
      <div className="metric-chart-head">
        <div>
          <span>{series.name}</span>
          <strong>{formatMetric(last)}</strong>
        </div>
        <small>{formatSignedDelta(first, last)}</small>
      </div>
      <svg className="metric-chart-svg" viewBox="0 0 260 96" role="img" aria-label={`${series.name} over steps`}>
        <line className="chart-axis" x1="12" x2="248" y1="82" y2="82" />
        {checkpointSteps.map((step) => (
          <line className="chart-marker" key={step} x1={xForStep(points, step)} x2={xForStep(points, step)} y1="14" y2="82" />
        ))}
        <polyline className="chart-line" points={polyline} />
      </svg>
      <div className="metric-chart-meta">
        <span>min {formatMetric(min)}</span>
        <span>max {formatMetric(max)}</span>
        <span>{points.length} points</span>
      </div>
    </article>
  );
}

function ComputeMetricStrip({ series }: { series: MetricSeries }) {
  const points = sortedPoints(series.points);
  const values = points.map((point) => point.metric_value);
  const max = Math.max(...values, 1);
  const last = values[values.length - 1];
  return (
    <article className="compute-strip">
      <div>
        <span>{series.name}</span>
        <strong>{formatMetric(last)}</strong>
      </div>
      <div className="compute-bars" aria-label={`${series.name} compute metric samples`}>
        {points.slice(-18).map((point) => (
          <span
            key={`${series.name}-${point.step}-${point.timestamp}`}
            style={{ height: `${Math.max(8, (point.metric_value / max) * 100)}%` }}
            title={`step ${point.step}: ${formatMetric(point.metric_value)}`}
          />
        ))}
      </div>
    </article>
  );
}

function OutcomeRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="outcome-row">
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

function EmptyState({ text }: { text: string }) {
  return <p className="subtle">{text}</p>;
}

function LineageFlow({ lineage }: { lineage: Array<{ lineage_step: string; source_type: string; source_id: number; target_type: string; target_id: number }> }) {
  if (!lineage.length) {
    return <EmptyState text="No lineage edges were submitted for this run." />;
  }
  return (
    <div className="run-lineage-stack">
      {lineage.map((edge, index) => (
        <article className="run-lineage-card" key={`${edge.lineage_step}-${edge.source_type}-${edge.source_id}-${edge.target_type}-${edge.target_id}`}>
          <span className="run-lineage-index">{index + 1}</span>
          <div className="run-lineage-body">
            <span className="run-lineage-label">{formatLineageStep(edge.lineage_step)}</span>
            <div className="run-lineage-entities">
              <LineageEntity label={edge.source_type} value={edge.source_id} />
              <span className="run-lineage-arrow">feeds</span>
              <LineageEntity label={edge.target_type} value={edge.target_id} />
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function LineageEntity({ label, value }: { label: string; value: number }) {
  return (
    <span className="run-lineage-entity">
      <span>{label.replaceAll("_", " ")}</span>
      <strong>{value}</strong>
    </span>
  );
}

function groupMetrics(metrics: RunMetric[]): MetricSeries[] {
  const grouped = new Map<string, RunMetric[]>();
  for (const metric of metrics) {
    if (!metric.metric_name) {
      continue;
    }
    grouped.set(metric.metric_name, [...(grouped.get(metric.metric_name) ?? []), metric]);
  }
  return [...grouped.entries()].map(([name, points]) => ({ name, points }));
}

function priorityMetricSeries(series: MetricSeries[]) {
  const priority = [
    "train.loss",
    "train.accuracy",
    "train.learning_rate",
    "train.grad_norm",
    "train.tokens_seen",
    "train.tokens_per_second",
    "throughput.tokens_per_second",
    "process.memory_rss_mb",
    "gpu.utilization_percent",
    "gpu.memory_used_gb",
    "cost.estimated_usd",
  ];
  return [...series]
    .sort((left, right) => {
      const leftIndex = priority.indexOf(left.name);
      const rightIndex = priority.indexOf(right.name);
      if (leftIndex === -1 && rightIndex === -1) {
        return left.name.localeCompare(right.name);
      }
      if (leftIndex === -1) {
        return 1;
      }
      if (rightIndex === -1) {
        return -1;
      }
      return leftIndex - rightIndex;
    })
    .slice(0, 6);
}

function chooseBestCheckpoint(checkpoints: RunCheckpoint[]) {
  const withAccuracy = checkpoints.filter((checkpoint) => checkpoint.metrics_snapshot["train.accuracy"] !== undefined);
  if (withAccuracy.length) {
    return highestBy(withAccuracy, (checkpoint) => checkpoint.metrics_snapshot["train.accuracy"]);
  }
  const withLoss = checkpoints.filter((checkpoint) => checkpoint.metrics_snapshot["train.loss"] !== undefined);
  if (withLoss.length) {
    return lowestBy(withLoss, (checkpoint) => checkpoint.metrics_snapshot["train.loss"]);
  }
  return highestBy(checkpoints, (checkpoint) => checkpoint.step);
}

function sortedPoints(points: RunMetric[]) {
  return [...points].sort((left, right) => left.step - right.step);
}

function svgPolyline(points: RunMetric[]) {
  const sorted = sortedPoints(points);
  if (sorted.length === 1) {
    return `12,48 248,48`;
  }
  const values = sorted.map((point) => point.metric_value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const yRange = max - min || 1;
  return sorted
    .map((point, index) => {
      const x = 12 + (index / Math.max(sorted.length - 1, 1)) * 236;
      const y = 82 - ((point.metric_value - min) / yRange) * 66;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function xForStep(points: RunMetric[], step: number) {
  const sorted = sortedPoints(points);
  if (!sorted.length) {
    return 12;
  }
  const minStep = sorted[0].step;
  const maxStep = sorted[sorted.length - 1].step;
  const range = maxStep - minStep || 1;
  return 12 + ((step - minStep) / range) * 236;
}

function lowestBy<T>(items: T[], selector: (item: T) => number): T | undefined {
  return items.reduce<T | undefined>((best, item) => {
    if (!best || selector(item) < selector(best)) {
      return item;
    }
    return best;
  }, undefined);
}

function highestBy<T>(items: T[], selector: (item: T) => number): T | undefined {
  return items.reduce<T | undefined>((best, item) => {
    if (!best || selector(item) > selector(best)) {
      return item;
    }
    return best;
  }, undefined);
}

function formatMetric(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
}

function formatMaybeNumber(value: number | undefined) {
  return value === undefined ? "n/a" : formatMetric(value);
}

function formatMaybePercent(value: number | undefined) {
  return value === undefined ? "n/a" : `${formatMetric(value)}%`;
}

function formatCount(value: number | undefined) {
  return value === undefined ? "n/a" : value.toLocaleString();
}

function formatSignedPercent(value: number | undefined) {
  if (value === undefined) {
    return "n/a";
  }
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function formatSignedDelta(first: number | undefined, last: number | undefined) {
  if (first === undefined || last === undefined) {
    return "n/a";
  }
  const delta = last - first;
  return `${delta > 0 ? "+" : ""}${formatMetric(delta)}`;
}

function formatConfigValue(value: unknown) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function formatLineageStep(value: string) {
  return value.replaceAll("_", " ");
}

function formatDateTime(value: string) {
  if (!value) {
    return "not available";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}

function formatDuration(startedAt: string, endedAt: string) {
  const start = Date.parse(startedAt);
  const end = Date.parse(endedAt);
  if (Number.isNaN(start) || Number.isNaN(end)) {
    return endedAt ? "duration unavailable" : "not completed";
  }
  const minutes = Math.max(0, Math.round((end - start) / 60000));
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}
