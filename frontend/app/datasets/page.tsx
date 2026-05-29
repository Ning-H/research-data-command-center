import { ArrowRight, Database, Plus } from "lucide-react";
import Link from "next/link";

import { listDatasets } from "../../lib/api";

export const dynamic = "force-dynamic";

export default async function DatasetsPage() {
  const datasets = await listDatasets();
  const totalRecords = datasets.reduce((sum, dataset) => sum + dataset.record_count, 0);
  const scored = datasets.filter((dataset) => dataset.asset_kind !== "raw");
  const averageQualityScore = scored.length
    ? Math.round(scored.reduce((sum, dataset) => sum + dataset.quality_score, 0) / scored.length)
    : 0;
  const sourceTypeCount = new Set(datasets.map((dataset) => dataset.source_label)).size;

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Data Assets</p>
          <h1>Catalog</h1>
          <p className="subtle">
            Real public datasets normalized into versioned records, quality metrics, and lineage.
          </p>
        </div>
        <Link className="btn btn--primary" href="/datasets/register">
          <Plus aria-hidden="true" size={16} />
          Register dataset
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Datasets</p>
          <p className="metric-value">{datasets.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Records</p>
          <p className="metric-value">{totalRecords.toLocaleString()}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Source types</p>
          <p className="metric-value">{sourceTypeCount}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Avg quality score</p>
          <p className="metric-value">{averageQualityScore}/100</p>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Purpose</th>
              <th>Version</th>
              <th>Records</th>
              <th>Quality</th>
              <th>Source</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {datasets.map((dataset) => {
              const isRaw = dataset.asset_kind === "raw";
              return (
                <tr key={`${dataset.dataset_id}-${dataset.dataset_version_id}`}>
                  <td>
                    <strong>{dataset.name}</strong>
                    {isRaw ? <span className="badge neutral raw-badge">RAW</span> : null}
                    <div className="muted-row">
                      {isRaw ? dataset.original_filename : dataset.source_dataset_name}
                    </div>
                    <div className="muted-row mono">dataset_id {dataset.dataset_id}</div>
                  </td>
                  <td>{dataset.data_purpose}</td>
                  <td>v{dataset.dataset_version_id}</td>
                  <td>{isRaw ? formatBytes(dataset.file_size_bytes) : dataset.record_count.toLocaleString()}</td>
                  <td>
                    {isRaw ? (
                      <span className="badge neutral">Unprocessed</span>
                    ) : (
                      <span className={qualityBadgeClass(dataset.quality_score)}>
                        {dataset.quality_score}/100 · {dataset.quality_label}
                      </span>
                    )}
                  </td>
                  <td>{dataset.source_label}</td>
                  <td>
                    <Link className="btn btn--secondary" href={`/datasets/${dataset.dataset_id}`}>
                      <Database aria-hidden="true" size={16} />
                      Detail
                      <ArrowRight aria-hidden="true" size={16} />
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function qualityBadgeClass(score: number) {
  if (score >= 90) {
    return "badge";
  }
  if (score >= 60) {
    return "badge warning";
  }
  return "badge danger";
}

function formatBytes(bytes: number) {
  if (!bytes) {
    return "—";
  }
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 10 || unit === 0 ? Math.round(value) : value.toFixed(1)} ${units[unit]}`;
}
