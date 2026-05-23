import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getDataset, type DatasetDetail } from "../../../lib/api";

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
          <p className="metric-label">Purpose</p>
          <p className="metric-value compact">{dataset.data_purpose}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Quality Score</p>
          <p className="metric-value">{dataset.quality_score}/100</p>
          <p className="metric-label">{dataset.quality_label}</p>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Source & Version</h2>
          <p className="subtle">Numeric platform IDs first; dataset names and source links remain human-readable.</p>
        </div>
        <div className="metadata-grid">
          <Metadata label="dataset_id" value={dataset.dataset_id} />
          <Metadata label="dataset_version_id" value={dataset.dataset_version_id} />
          <Metadata label="dataset_name" value={dataset.name} />
          <Metadata label="registration_date" value={formatDate(dataset.registration_date)} />
          <Metadata label="last_updated_date" value={formatDate(dataset.last_updated_date)} />
          <Metadata label="data_purpose" value={dataset.data_purpose} />
          <Metadata label="data_format" value={dataset.data_format} />
          <Metadata label="query_engine" value={dataset.query_engine} />
          <Metadata label="source_link" value={dataset.source_dataset_name} href={dataset.source_url} />
          <Metadata label="record_count" value={dataset.record_count.toLocaleString()} />
          <Metadata label="source_label" value={dataset.source_label} />
          <Metadata label="mean_tokens" value={formatMetric(metrics["tokens.mean"])} />
          <Metadata label="quality_score" value={`${dataset.quality_score}/100`} />
          <Metadata label="quality_label" value={dataset.quality_label} />
        </div>
        <div className="description-box">
          <span>dataset_description</span>
          <p>{dataset.description}</p>
        </div>
      </div>

      <QualityPanel dataset={dataset} />

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Records</h2>
            <p className="subtle">Normalized examples from the dataset version.</p>
          </div>
          <div className="record-list">
            {dataset.sample_records.slice(0, 5).map((record) => (
              <article className="record" key={`${dataset.dataset_id}-${dataset.dataset_version_id}-${record.record_id}`}>
                <div className="muted-row">
                  {record.category} · record_id {record.record_id}
                </div>
                <h3>{record.instruction}</h3>
                <Metadata label="record_id" value={record.record_id} />
                <Metadata label="source_row_id" value={record.source_row_id} />
                {record.question ? <RecordBlock label="Question" value={record.question} /> : null}
                {record.input_text ? <RecordBlock label="Input" value={record.input_text} /> : null}
                {record.chosen_text ? <RecordBlock label="Chosen" value={record.chosen_text} /> : null}
                {record.rejected_text ? <RecordBlock label="Rejected" value={record.rejected_text} /> : null}
                {record.target_text ? <RecordBlock label="Target" value={record.target_text} /> : null}
              </article>
            ))}
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
                  <th>Nulls</th>
                  <th>Distinct</th>
                  <th>Mean length</th>
                </tr>
              </thead>
              <tbody>
                {dataset.schema_profile.map((field) => (
                  <tr key={field.field_name}>
                    <td>{field.field_name}</td>
                    <td>{field.non_null_count.toLocaleString()}</td>
                    <td>{field.null_count.toLocaleString()}</td>
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
              <Metadata label="source_dataset_version_id" value={edge.source_dataset_version_id || edge.source_label} />
              <Metadata label="target_dataset_version_id" value={edge.target_dataset_version_id} />
              <Metadata label="created_by_user_id" value={edge.created_by_user_id} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function QualityPanel({ dataset }: { dataset: DatasetDetail }) {
  return (
    <div className="panel quality-panel">
      <div className="quality-header">
        <div>
          <h2>Quality</h2>
          <p className="subtle">{dataset.quality_summary.meaning}</p>
        </div>
        <div className="score-card">
          <span>quality_score</span>
          <strong>{dataset.quality_summary.score}/100</strong>
          <p>{dataset.quality_summary.score_label}</p>
        </div>
      </div>

      <div className="quality-note">
        <span className={qualityBadgeClass(dataset.quality_summary.score)}>
          {dataset.quality_summary.score_label}
        </span>
        <p>{dataset.quality_summary.score_explanation}</p>
        <p>{dataset.quality_summary.null_value_policy}</p>
        <div className="muted-row">
          Required fields: {dataset.quality_summary.required_fields.join(", ")} · null values measured:{" "}
          {dataset.quality_summary.total_null_values.toLocaleString()} across{" "}
          {dataset.quality_summary.fields_with_nulls.toLocaleString()} fields
        </div>
      </div>

      <div className="quality-checks">
        {dataset.quality_summary.checks.map((check) => (
          <div className="quality-check" key={check.metric_name}>
            <div>
              <strong>{check.name}</strong>
              <span className={check.status === "ok" ? "badge" : check.status === "review" ? "badge warning" : "badge neutral"}>
                {check.status}
              </span>
            </div>
            <p>{check.description}</p>
            <div className="muted-row">
              {check.metric_name}: {formatMetric(check.metric_value)}
            </div>
          </div>
        ))}
      </div>

      <div className="component-grid">
        {dataset.quality_summary.score_components.map((component) => (
          <div className="component-card" key={component.name}>
            <span>{component.weight} pts</span>
            <strong>{component.name}</strong>
            <p>{component.description}</p>
          </div>
        ))}
      </div>

      <div className="table-wrap compact-table">
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
  );
}

function Metadata({ label, value, href }: { label: string; value: string | number; href?: string }) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      {href ? (
        <a href={href} rel="noreferrer" target="_blank">
          {value}
        </a>
      ) : (
        <strong>{value}</strong>
      )}
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

function formatDate(value: string) {
  return value.slice(0, 10);
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
