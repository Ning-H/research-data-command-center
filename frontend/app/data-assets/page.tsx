import { ArrowRight, Database, Layers, ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { listDatasets } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function DataAssetsPage() {
  const datasets = await listDatasets();
  const totalRecords = datasets.reduce((sum, dataset) => sum + dataset.record_count, 0);
  const avgQuality = datasets.length
    ? Math.round(datasets.reduce((sum, dataset) => sum + dataset.quality_score, 0) / datasets.length)
    : 0;
  const publicReal = datasets.filter((dataset) => dataset.source_label === "PUBLIC_REAL").length;

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Data Assets</p>
          <h1>Data Asset Registry</h1>
          <p className="subtle">
            Register all research data, not only training datasets: SFT data, preference data,
            eval datasets, safety/red-team data, inference trace samples, and failure-derived data.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/datasets">
          Legacy dataset catalog
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Assets registered</p>
          <p className="metric-value">{datasets.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Records indexed</p>
          <p className="metric-value">{totalRecords.toLocaleString()}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Avg quality score</p>
          <p className="metric-value">{avgQuality}/100</p>
        </div>
        <div className="metric">
          <p className="metric-label">PUBLIC_REAL</p>
          <p className="metric-value">{publicReal}</p>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Expanded Data Asset Types</h2>
          <p className="subtle">
            The existing dataset registry becomes the foundation for data assets and future data
            mixtures.
          </p>
        </div>
        <div className="component-grid">
          <AssetType icon={<Database aria-hidden="true" size={18} />} title="Post-training data">
            Instruction SFT, coding explanations, algorithm references, study-guide examples, and QA.
          </AssetType>
          <AssetType icon={<ShieldCheck aria-hidden="true" size={18} />} title="Eval and safety data">
            Eval datasets, red-team data, over-refusal examples, and benchmark tasks.
          </AssetType>
          <AssetType icon={<Layers aria-hidden="true" size={18} />} title="Data mixtures">
            Planned mixtures like instruction data, coding explanations, outlines, and failure-derived corrections.
          </AssetType>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Asset</th>
              <th>Purpose</th>
              <th>Format</th>
              <th>Quality</th>
              <th>Source</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {datasets.map((dataset) => (
              <tr key={dataset.dataset_id}>
                <td>
                  <strong>{dataset.name}</strong>
                  <div className="muted-row mono">dataset_id {dataset.dataset_id}</div>
                  <div className="muted-row mono">dataset_version_id {dataset.dataset_version_id}</div>
                </td>
                <td>
                  {dataset.data_purpose}
                  <div className="muted-row">{dataset.category}</div>
                </td>
                <td>
                  {dataset.data_format}
                  <div className="muted-row">{dataset.query_engine}</div>
                </td>
                <td>
                  {dataset.quality_score}/100
                  <div className="muted-row">{dataset.quality_label}</div>
                </td>
                <td>
                  <span className="badge">{dataset.source_label}</span>
                  <div className="muted-row">{dataset.source_dataset_name}</div>
                </td>
                <td>
                  <Link className="btn btn--secondary" href={`/datasets/${dataset.dataset_id}`}>
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

function AssetType({
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
