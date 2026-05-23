import { ArrowRight, Database } from "lucide-react";
import Link from "next/link";

import { listDatasets } from "../../lib/api";

export default async function DatasetsPage() {
  const datasets = await listDatasets();
  const totalRecords = datasets.reduce((sum, dataset) => sum + dataset.record_count, 0);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Datasets</p>
          <h1>Catalog</h1>
          <p className="subtle">
            Real public datasets normalized into versioned records, quality metrics, and lineage.
          </p>
        </div>
        <span className="badge">API-backed</span>
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
          <p className="metric-label">Data source</p>
          <p className="metric-value">PUBLIC_REAL</p>
        </div>
        <div className="metric">
          <p className="metric-label">Quality gate</p>
          <p className="metric-value">
            {datasets.every((dataset) => dataset.quality_status === "passed") ? "Passed" : "Review"}
          </p>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Dataset ID</th>
              <th>Task</th>
              <th>Version</th>
              <th>Records</th>
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
                  <div className="muted-row">{dataset.source_dataset_name}</div>
                </td>
                <td className="mono">{dataset.dataset_id}</td>
                <td>{dataset.category}</td>
                <td>{dataset.dataset_version_id}</td>
                <td>{dataset.record_count.toLocaleString()}</td>
                <td>
                  <span className={dataset.quality_status === "passed" ? "badge" : "badge warning"}>
                    {dataset.quality_status}
                  </span>
                </td>
                <td>{dataset.source_label}</td>
                <td>
                  <Link className="button secondary" href={`/datasets/${dataset.dataset_id}`}>
                    <Database aria-hidden="true" size={16} />
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
