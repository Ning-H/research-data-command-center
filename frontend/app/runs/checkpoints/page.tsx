import { ArrowRight, Medal } from "lucide-react";
import Link from "next/link";

import { searchCheckpoints } from "../../../lib/api";

type CheckpointsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function CheckpointsPage({ searchParams = {} }: CheckpointsPageProps) {
  const filters = normalizeFilters(searchParams);
  const checkpoints = await searchCheckpoints(filters);
  const best = checkpoints[0];

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Runs / Checkpoints</p>
          <h1>Checkpoint Search</h1>
          <p className="subtle">
            Compare checkpoints across completed runs that used the same governed dataset,
            trainer, and framework. The top result is the best promotion candidate for the
            selected ranking rule.
          </p>
        </div>
        <Link className="button secondary" href="/runs">
          Runs
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <div className="panel">
        <div>
          <h2>Current Filter</h2>
          <p className="subtle">
            Checkpoint metadata is stored in the checkpoint table for cross-run search. The
            checkpoint artifact files stay under run-owned object-store paths because the training
            job created them during that run.
          </p>
        </div>
        <div className="metadata-grid">
          <Metadata label="dataset_id" value={filters.dataset_id} />
          <Metadata label="dataset_version_id" value={filters.dataset_version_id} />
          <Metadata label="framework" value={filters.framework} />
          <Metadata label="trainer" value={filters.trainer} />
          <Metadata label="ranking_metric" value={filters.ranking_metric} />
          <Metadata label="direction" value={filters.direction} />
        </div>
      </div>

      {best ? (
        <div className="panel">
          <div>
            <h2>Best Checkpoint</h2>
            <p className="subtle">
              Ranked by {best.ranking_metric} with lower train.loss as the tie-break.
            </p>
          </div>
          <div className="component-grid">
            <div className="component-card">
              <span>
                <Medal aria-hidden="true" size={18} />
              </span>
              <strong>checkpoint_id {best.checkpoint_id}</strong>
              <p>{best.run_name}</p>
            </div>
            <MetricCard label="run_id" value={best.run_id} />
            <MetricCard label="step" value={best.step} />
            <MetricCard label={best.ranking_metric} value={formatMetric(best.ranking_value)} />
            <MetricCard label="train.loss" value={formatMetric(best.metrics_snapshot["train.loss"])} />
          </div>
        </div>
      ) : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Rank</th>
              <th>Checkpoint</th>
              <th>Run</th>
              <th>Dataset</th>
              <th>Framework / Trainer</th>
              <th>Score</th>
              <th>Loss</th>
              <th>Artifact</th>
            </tr>
          </thead>
          <tbody>
            {checkpoints.map((checkpoint) => (
              <tr key={checkpoint.checkpoint_id}>
                <td>
                  <span className={checkpoint.is_best_for_filter ? "badge" : "badge neutral"}>
                    #{checkpoint.rank}
                  </span>
                </td>
                <td>
                  <strong>checkpoint_id {checkpoint.checkpoint_id}</strong>
                  <div className="muted-row">step {checkpoint.step}</div>
                  <div className="muted-row">{checkpoint.status}</div>
                </td>
                <td>
                  <Link href={`/runs/${checkpoint.run_id}`}>run_id {checkpoint.run_id}</Link>
                  <div className="muted-row">{checkpoint.run_name}</div>
                </td>
                <td>
                  dataset_id {checkpoint.dataset_id}
                  <div className="muted-row">dataset_version_id {checkpoint.dataset_version_id}</div>
                </td>
                <td>
                  {checkpoint.framework}
                  <div className="muted-row">{checkpoint.device}</div>
                  <div className="muted-row">{checkpoint.trainer}</div>
                </td>
                <td>{formatMetric(checkpoint.ranking_value)}</td>
                <td>{formatMetric(checkpoint.metrics_snapshot["train.loss"])}</td>
                <td>
                  <span className="mono">{checkpoint.checkpoint_uri}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function normalizeFilters(searchParams: Record<string, string | string[] | undefined>) {
  return {
    dataset_id: first(searchParams.dataset_id) ?? "1",
    dataset_version_id: first(searchParams.dataset_version_id) ?? "1",
    framework: first(searchParams.framework) ?? "pytorch",
    trainer: first(searchParams.trainer) ?? "train_registered_torch_classifier",
    ranking_metric: first(searchParams.ranking_metric) ?? "train.accuracy",
    direction: first(searchParams.direction) ?? "desc",
  };
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function Metadata({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="component-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatMetric(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return "not logged";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
}
