import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getDataset } from "../../../lib/api";

type DatasetDetailPageProps = {
  params: {
    datasetId: string;
  };
};

export default async function DatasetDetailPage({ params }: DatasetDetailPageProps) {
  let dataset;
  try {
    dataset = await getDataset(params.datasetId);
  } catch {
    notFound();
  }

  const metrics = Object.fromEntries(
    dataset.quality_metrics.map((metric) => [metric.metric_name, metric.metric_value])
  );

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Dataset Detail</p>
          <h1>{dataset.name}</h1>
          <p className="subtle">{dataset.description}</p>
        </div>
        <Link className="button secondary" href="/datasets">
          <ArrowLeft aria-hidden="true" size={16} />
          Catalog
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Dataset</p>
          <p className="metric-value compact">{dataset.name}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Records</p>
          <p className="metric-value">{dataset.record_count.toLocaleString()}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Task</p>
          <p className="metric-value compact">{dataset.category}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Quality</p>
          <p className="metric-value">{dataset.quality_status}</p>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Source & Version</h2>
          <p className="subtle">Human-readable source first; stable IDs remain available for lineage, APIs, and joins.</p>
        </div>
        <div className="metadata-grid">
          <Metadata label="dataset_name" value={dataset.name} />
          <Metadata label="public_source" value={dataset.source_dataset_name} />
          <Metadata label="record_count" value={dataset.record_count.toLocaleString()} />
          <Metadata label="dataset_id" value={dataset.dataset_id} />
          <Metadata label="dataset_version_id" value={dataset.dataset_version_id} />
          <Metadata label="source_label" value={dataset.source_label} />
          <Metadata label="task_type" value={dataset.task_type} />
          <Metadata label="mean_tokens" value={formatMetric(metrics["tokens.mean"])} />
          <Metadata label="quality_status" value={dataset.quality_status} />
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Records</h2>
            <p className="subtle">Normalized examples from the dataset version.</p>
          </div>
          <div className="record-list">
            {dataset.sample_records.slice(0, 5).map((record) => (
              <article className="record" key={record.record_id}>
                <div className="muted-row">
                  {record.category} · row {record.source_row_id}
                </div>
                <h3>{record.instruction}</h3>
                <Metadata label="record_id" value={record.record_id} />
                {record.question ? <RecordBlock label="Question" value={record.question} /> : null}
                {record.input_text ? <RecordBlock label="Input" value={record.input_text} /> : null}
                {record.chosen_text ? <RecordBlock label="Chosen" value={record.chosen_text} /> : null}
                {record.rejected_text ? <RecordBlock label="Rejected" value={record.rejected_text} /> : null}
                {record.target_text ? <RecordBlock label="Target" value={record.target_text} /> : null}
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Quality</h2>
            <p className="subtle">Generated metrics from the local profiling pipeline.</p>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {dataset.quality_metrics.map((metric) => (
                  <tr key={metric.metric_name}>
                    <td>{metric.metric_name}</td>
                    <td>{formatMetric(metric.metric_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Schema</h2>
            <p className="subtle">Field-level profile for the normalized Parquet records.</p>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Non-null</th>
                  <th>Distinct</th>
                  <th>Mean length</th>
                </tr>
              </thead>
              <tbody>
                {dataset.schema_profile.map((field) => (
                  <tr key={field.field_name}>
                    <td>{field.field_name}</td>
                    <td>{field.non_null_count.toLocaleString()}</td>
                    <td>{field.distinct_count.toLocaleString()}</td>
                    <td>{formatMetric(field.mean_length)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Lineage & Usage</h2>
            <p className="subtle">Dataset-version lineage now; run/model usage attaches in later slices.</p>
          </div>
          {dataset.lineage.map((edge) => (
            <div className="record" key={`${edge.lineage_event_type}-${edge.target_dataset_version_id}`}>
              <span className="badge">{edge.lineage_event_type}</span>
              <h3>{edge.transform_name}</h3>
              <Metadata label="dataset_id" value={edge.dataset_id} />
              <Metadata label="source_dataset_version_id" value={edge.source_dataset_version_id || "public source"} />
              <Metadata label="target_dataset_version_id" value={edge.target_dataset_version_id} />
              <Metadata label="created_by_user_id" value={edge.created_by_user_id} />
            </div>
          ))}
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

function RecordBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="muted-row">{label}</div>
      <p className="record-text">{truncate(value, 900)}</p>
    </div>
  );
}

function truncate(value: string, maxLength: number) {
  if (value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength)}...`;
}

function formatMetric(value: number | undefined) {
  if (value === undefined) {
    return "0";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
}
