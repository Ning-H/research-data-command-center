import Link from "next/link";
import { ArrowLeft, ExternalLink } from "lucide-react";
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

        <div className="dataset-hero-panel dataset-hero-panel--wide">
          <div className="dataset-hero-topline">
            <div className="dataset-kicker">
              <span className="badge neutral">{dataset.data_structure.toUpperCase()}</span>
              <span>{dataset.category}</span>
              <span>dataset_id {dataset.dataset_id}</span>
              <span>v{dataset.dataset_version_id}</span>
            </div>
            <div className="dataset-actions">
              <Link className="btn btn--secondary btn--sm" href="/datasets">
                <ArrowLeft aria-hidden="true" size={15} />
                Catalog
              </Link>
            </div>
          </div>
          <h1>{dataset.name}</h1>
          <p className="dataset-hero-desc">
            This asset is stored as-is in object storage. It has not been parsed, profiled, or
            quality-scored.
          </p>

          <div className="dataset-fact-grid dataset-fact-grid--raw">
            <DatasetFact label="Data structure" value={dataset.data_structure} />
            <DatasetFact label="Category" value={dataset.category} />
            <DatasetFact label="Version" value={`v${dataset.dataset_version_id}`} />
            <DatasetFact label="File" value={dataset.original_filename} mono />
            <DatasetFact label="Size" value={formatBytes(dataset.file_size_bytes)} />
            <DatasetFact label="Type" value={dataset.content_type || dataset.data_format} />
            <DatasetFact label="Source" value={dataset.source_label} />
            {dataset.description && (
              <DatasetFact label="Description" value={dataset.description} wide />
            )}
            <DatasetFact label="Object URI" value={dataset.raw_object_uri} mono wide />
            <DatasetFact label="Registered" value={formatDate(dataset.registration_date)} />
            <DatasetFact label="Updated" value={formatDate(dataset.last_updated_date)} />
          </div>
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

      <div className="dataset-overview">
        <div className="dataset-hero-panel">
          <div className="dataset-hero-topline">
            <div className="dataset-kicker">
              <span className="badge">Structured dataset</span>
              <span>dataset_id {dataset.dataset_id}</span>
              <span>v{dataset.dataset_version_id}</span>
            </div>
            <div className="dataset-actions">
              <Link className="btn btn--secondary btn--sm" href="/datasets">
                <ArrowLeft aria-hidden="true" size={15} />
                Catalog
              </Link>
              {isExternalUrl(dataset.source_url) && (
                <a
                  className="btn btn--dark btn--sm"
                  href={dataset.source_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  Source
                  <ExternalLink aria-hidden="true" size={14} />
                </a>
              )}
            </div>
          </div>

          <h1>{dataset.name}</h1>
          {dataset.description && <p className="dataset-hero-desc">{dataset.description}</p>}

          <div className="dataset-fact-grid">
            <DatasetFact label="Version" value={`v${dataset.dataset_version_id}`} />
            <DatasetFact label="Records" value={dataset.record_count.toLocaleString()} />
            <DatasetFact label="Format" value={dataset.data_format} />
            <DatasetFact
              label="Quality"
              value={`${dataset.quality_score}/100 · ${dataset.quality_label}`}
              valueClassName={qualityMetaClass(dataset.quality_score)}
            />
            <DatasetFact label="Registered" value={formatDate(dataset.registration_date)} />
            <DatasetFact label="Updated" value={formatDate(dataset.last_updated_date)} />
          </div>
        </div>

        <aside className="dataset-schema-panel">
          <div className="dataset-schema-head">
            <span className="doc-label">Schema</span>
            <span>{dataset.schema_profile.length} fields</span>
          </div>
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
        </aside>
      </div>

      <DatasetTabs dataset={dataset} />
    </section>
  );
}

function DatasetFact({
  label,
  value,
  mono = false,
  strong = false,
  wide = false,
  valueClassName = "",
}: {
  label: string;
  value: string;
  mono?: boolean;
  strong?: boolean;
  wide?: boolean;
  valueClassName?: string;
}) {
  const classes = [
    "dataset-fact",
    wide ? "dataset-fact--wide" : "",
    mono ? "dataset-fact--mono" : "",
    strong ? "dataset-fact--strong" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes}>
      <span>{label}</span>
      <strong className={valueClassName}>{value}</strong>
    </div>
  );
}

function qualityMetaClass(score: number) {
  if (score >= 90) return "meta-quality good";
  if (score >= 60) return "meta-quality warn";
  return "meta-quality bad";
}

function isExternalUrl(value: string) {
  return value.startsWith("http://") || value.startsWith("https://");
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
