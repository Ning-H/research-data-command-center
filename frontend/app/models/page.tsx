import { ArrowRight, Boxes, GitBranch, ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { listModels } from "../../lib/api";

export default async function ModelsPage() {
  const models = await listModels();
  const uniqueModels = new Set(models.map((model) => model.model_id)).size;
  const candidateCount = models.filter((model) => model.status === "candidate").length;
  const promotedCount = models.filter((model) => model.status === "promoted").length;

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Models & Checkpoints</p>
          <h1>Model Registry</h1>
          <p className="subtle">
            Register candidate model versions from promoted checkpoints. Each model version keeps
            the checkpoint, training run, data asset, and artifact lineage needed for later evaluation.
          </p>
        </div>
        <Link className="button secondary" href="/runs/checkpoints">
          Find checkpoints
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Model families</p>
          <p className="metric-value">{uniqueModels}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Model versions</p>
          <p className="metric-value">{models.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Candidates</p>
          <p className="metric-value">{candidateCount}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Promoted</p>
          <p className="metric-value">{promotedCount}</p>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Registry Boundary</h2>
          <p className="subtle">
            Researchers choose a checkpoint to register. The platform derives the training run and
            data asset lineage from `checkpoint_id`, then stores immutable model-version metadata.
          </p>
        </div>
        <div className="component-grid">
          <WorkflowCard icon={<Boxes aria-hidden="true" size={18} />} title="Checkpoint input">
            Promotion starts from one checkpoint that already belongs to one run.
          </WorkflowCard>
          <WorkflowCard icon={<GitBranch aria-hidden="true" size={18} />} title="Derived lineage">
            Dataset, run, checkpoint, and artifact references are copied from source metadata.
          </WorkflowCard>
          <WorkflowCard icon={<ShieldCheck aria-hidden="true" size={18} />} title="Evaluation ready">
            Eval runs attach to `model_version_id`, not directly to loose checkpoint paths.
          </WorkflowCard>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Model Version</th>
              <th>Source Checkpoint</th>
              <th>Dataset</th>
              <th>Status</th>
              <th>Best Metric</th>
              <th>Intended Use</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {models.map((model) => (
              <tr key={model.model_version_id}>
                <td>
                  <strong>{model.model_version_name}</strong>
                  <div className="muted-row">{model.model_name}</div>
                  <div className="muted-row mono">model_version_id {model.model_version_id}</div>
                  <div className="muted-row mono">model_id {model.model_id}</div>
                </td>
                <td>
                  checkpoint_id {model.checkpoint_id}
                  <div className="muted-row">run_id {model.run_id}</div>
                  <div className="muted-row">step {model.source_checkpoint_step}</div>
                </td>
                <td>
                  dataset_id {model.dataset_id}
                  <div className="muted-row">dataset_version_id {model.dataset_version_id}</div>
                </td>
                <td>
                  <span className={model.status === "promoted" ? "badge" : "badge neutral"}>
                    {model.status}
                  </span>
                </td>
                <td>
                  train.accuracy {formatMetric(model.metrics_snapshot["train.accuracy"])}
                  <div className="muted-row">train.loss {formatMetric(model.metrics_snapshot["train.loss"])}</div>
                </td>
                <td>{model.intended_use || "not provided"}</td>
                <td>
                  <Link className="button secondary" href={`/models/${model.model_version_id}`}>
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

function WorkflowCard({
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

function formatMetric(value: number | undefined) {
  if (value === undefined) {
    return "not logged";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
}
