import Link from "next/link";
import { notFound } from "next/navigation";

import { getDataset, type DatasetDetail } from "../../../lib/api";
import DatasetTabs from "./DatasetTabs";

type DatasetDetailPageProps = {
  params: { datasetId: string };
};

export default async function DatasetDetailPage({ params }: DatasetDetailPageProps) {
  let dataset: DatasetDetail;
  try {
    dataset = await getDataset(params.datasetId);
  } catch {
    notFound();
  }

  if (dataset.asset_kind === "raw") {
    return (
      <section className="page dataset-detail-page">
        <nav className="breadcrumb">
          <Link href="/datasets">Datasets</Link>
          <span className="breadcrumb-sep" aria-hidden="true">/</span>
          <span>{dataset.name}</span>
        </nav>

        <div className="dataset-overview-left">
          <div className="raw-asset-heading">
            <span className="badge neutral raw-badge">RAW</span>
            <p className="subtle">
              This asset is stored as-is in object storage. It has not been parsed, profiled, or
              quality-scored.
            </p>
          </div>
          <dl className="dataset-props">
            <div className="dataset-prop-row">
              <dt>Name</dt>
              <dd className="dataset-prop-name">{dataset.name}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Version</dt>
              <dd>v{dataset.dataset_version_id}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>File</dt>
              <dd className="mono">{dataset.original_filename}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Size</dt>
              <dd>{formatBytes(dataset.file_size_bytes)}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Type</dt>
              <dd>{dataset.content_type || dataset.data_format}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Source</dt>
              <dd>{dataset.source_label}</dd>
            </div>
            {dataset.description && (
              <div className="dataset-prop-row">
                <dt>Description</dt>
                <dd className="dataset-prop-desc">{dataset.description}</dd>
              </div>
            )}
            <div className="dataset-prop-row">
              <dt>Object URI</dt>
              <dd className="mono dataset-prop-desc">{dataset.raw_object_uri}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Registered</dt>
              <dd>{formatDate(dataset.registration_date)}</dd>
            </div>
          </dl>
        </div>
      </section>
    );
  }

  return (
    <section className="page dataset-detail-page">
      <nav className="breadcrumb">
        <Link href="/datasets">Datasets</Link>
        <span className="breadcrumb-sep" aria-hidden="true">/</span>
        <span>{dataset.name}</span>
      </nav>

      {/* Two-column: left = name/description/stats, right = schema */}
      <div className="dataset-overview">
        <div className="dataset-overview-left">
          <dl className="dataset-props">
            <div className="dataset-prop-row">
              <dt>Name</dt>
              <dd className="dataset-prop-name">{dataset.name}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Version</dt>
              <dd>v{dataset.dataset_version_id}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Records</dt>
              <dd>{dataset.record_count.toLocaleString()}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Format</dt>
              <dd>{dataset.data_format}</dd>
            </div>
            {dataset.description && (
              <div className="dataset-prop-row">
                <dt>Description</dt>
                <dd className="dataset-prop-desc">{dataset.description}</dd>
              </div>
            )}
            <div className="dataset-prop-row">
              <dt>Quality</dt>
              <dd className={qualityMetaClass(dataset.quality_score)}>
                {dataset.quality_score}/100 · {dataset.quality_label}
              </dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Registered</dt>
              <dd>{formatDate(dataset.registration_date)}</dd>
            </div>
            <div className="dataset-prop-row">
              <dt>Updated</dt>
              <dd>{formatDate(dataset.last_updated_date)}</dd>
            </div>
          </dl>
        </div>

        <div className="dataset-overview-right">
          <span className="doc-label">Schema</span>
          <div className="schema-field-list">
            {dataset.schema_profile.map((field) => (
              <div className="schema-field-row" key={field.field_name}>
                <span className="mono schema-field-name">{field.field_name}</span>
                {field.field_type ? (
                  <span className="schema-field-type">{field.field_type}</span>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Tabs: Sample Records | Source & Lineage | Quality & Metrics */}
      <DatasetTabs dataset={dataset} />
    </section>
  );
}

function qualityMetaClass(score: number) {
  if (score >= 90) return "meta-quality good";
  if (score >= 60) return "meta-quality warn";
  return "meta-quality bad";
}

function formatBytes(bytes: number) {
  if (!bytes) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value >= 10 || unit === 0 ? Math.round(value) : value.toFixed(1)} ${units[unit]}`;
}

function formatDate(value: string) {
  try {
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return value;
  }
}
