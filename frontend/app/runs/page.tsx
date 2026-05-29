import { ArrowRight, Database, GitBranch, RadioTower } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { listRuns } from "../../lib/api";

export default async function RunsPage() {
  const runs = await listRuns();
  const completedRuns = runs.filter((run) => run.status === "completed").length;
  const checkpointCount = runs.reduce((sum, run) => sum + run.checkpoint_count, 0);
  const averageHealth = runs.length
    ? Math.round(runs.reduce((sum, run) => sum + run.health_summary.health_score, 0) / runs.length)
    : 0;

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Training Runs</p>
          <h1>Training Run Records</h1>
          <p className="subtle">
            Researchers train wherever they already train. Their scripts save raw run events,
            checkpoint metadata, run type, and configs here for normalization, lineage, and analysis.
          </p>
        </div>
        <div className="action-row">
          <Link className="btn btn--secondary" href="/runs/checkpoints">
            Checkpoints
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
          <span className="badge">API / SDK ingest</span>
        </div>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Runs ingested</p>
          <p className="metric-value">{runs.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Completed</p>
          <p className="metric-value">{completedRuns}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Checkpoints tracked</p>
          <p className="metric-value">{checkpointCount}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Avg health score</p>
          <p className="metric-value">{averageHealth}/100</p>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Platform Boundary</h2>
          <p className="subtle">
            This app does not launch the training job. It receives raw logs and metadata from
            researcher-owned jobs, then processes them into canonical metrics, checkpoints, health
            summaries, and lineage. Future run types include pretraining, continued pretraining,
            SFT, DPO, RLHF, RLAIF, reward-model training, distillation, and finetuning.
          </p>
        </div>
        <div className="component-grid">
          <VisionCard icon={<RadioTower aria-hidden="true" size={18} />} title="Raw ingest">
            API/SDK calls save run configs, metric events, and checkpoint metadata.
          </VisionCard>
          <VisionCard icon={<Database aria-hidden="true" size={18} />} title="Processing">
            Raw events become long-format training and compute metric tables.
          </VisionCard>
          <VisionCard icon={<GitBranch aria-hidden="true" size={18} />} title="Lineage">
            Dataset version connects to run config, run, checkpoints, and later model versions.
          </VisionCard>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Dataset</th>
              <th>Status</th>
              <th>Health</th>
              <th>Checkpoints</th>
              <th>Data source</th>
              <th>Ingest source</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id}>
                <td>
                  <strong>{run.run_name}</strong>
                  <div className="muted-row">{run.experiment_name}</div>
                  <div className="muted-row mono">run_id {run.run_id}</div>
                </td>
                <td>
                  dataset_id {run.dataset_id}
                  <div className="muted-row">dataset_version_id {run.dataset_version_id}</div>
                </td>
                <td>
                  <span className={run.status === "failed" ? "badge warning" : "badge"}>
                    {run.status}
                  </span>
                </td>
                <td>
                  {run.health_summary.health_score}/100
                  <div className="muted-row">{run.health_summary.health_label}</div>
                </td>
                <td>{run.checkpoint_count}</td>
                <td>
                  <span className={run.source_priority === "GENERATED_REAL" ? "badge" : "badge neutral"}>
                    {run.source_priority}
                  </span>
                </td>
                <td>{run.ingest_source}</td>
                <td>
                  <Link className="btn btn--secondary" href={`/runs/${run.run_id}`}>
                    Detail
                    <ArrowRight aria-hidden="true" size={16} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function VisionCard({
  children,
  icon,
  title,
}: {
  children: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <div className="component-card">
      <span>{icon}</span>
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  );
}
