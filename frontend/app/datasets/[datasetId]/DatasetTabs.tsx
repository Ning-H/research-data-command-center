"use client";

import { useState } from "react";
import type { DatasetDetail } from "../../../lib/api";

type Tab = "records" | "lineage" | "quality";

type Props = {
  dataset: Pick<
    DatasetDetail,
    | "sample_records"
    | "lineage"
    | "source_url"
    | "source_dataset_name"
    | "source_label"
    | "query_engine"
    | "dataset_id"
    | "dataset_version_id"
    | "data_format"
    | "quality_summary"
    | "quality_metrics"
  >;
};

export default function DatasetTabs({ dataset }: Props) {
  const [active, setActive] = useState<Tab>("records");
  const [showMethodology, setShowMethodology] = useState(false);

  return (
    <div className="dataset-tabs">
      <div className="tab-bar" role="tablist">
        <button
          className={`tab-btn${active === "records" ? " active" : ""}`}
          onClick={() => setActive("records")}
          role="tab"
          aria-selected={active === "records"}
        >
          Sample Records
        </button>
        <button
          className={`tab-btn${active === "lineage" ? " active" : ""}`}
          onClick={() => setActive("lineage")}
          role="tab"
          aria-selected={active === "lineage"}
        >
          Source & Lineage
        </button>
        <button
          className={`tab-btn${active === "quality" ? " active" : ""}`}
          onClick={() => setActive("quality")}
          role="tab"
          aria-selected={active === "quality"}
        >
          Quality & Metrics
        </button>
      </div>

      {active === "records" && (
        <div className="tab-panel">
          {dataset.sample_records.length === 0 ? (
            <p className="doc-text empty">No sample records available.</p>
          ) : (
            <div className="sample-record-list">
              {dataset.sample_records.slice(0, 5).map((record, idx) => {
                const bodyFields = (
                  Object.entries(record) as [string, unknown][]
                ).filter(
                  ([key, val]) =>
                    key !== "record_id" &&
                    key !== "category" &&
                    val !== null &&
                    val !== undefined &&
                    val !== ""
                );
                return (
                  <div className="sample-record-card" key={record.record_id}>
                    <div className="sample-record-header">
                      <span className="sample-record-num">Record {idx + 1}</span>
                      <span className="badge neutral">{record.category}</span>
                      <span className="muted-row">#{record.record_id}</span>
                    </div>
                    <div className="sample-record-body">
                      {bodyFields.map(([key, val]) => (
                        <div className="sample-record-field" key={key}>
                          <span className="sample-record-key mono">{key}</span>
                          <span className="sample-record-val">{String(val)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {active === "lineage" && (
        <div className="tab-panel">
          {/* Identity metadata with human-readable labels */}
          <div className="lineage-meta-table">
            <LineageMeta label="Dataset ID" value={String(dataset.dataset_id)} />
            <LineageMeta label="Version" value={`v${dataset.dataset_version_id}`} />
            <LineageMeta label="Source" value={dataset.source_label} />
            <LineageMeta label="Format" value={dataset.data_format} />
            <LineageMeta label="Query Engine" value={dataset.query_engine} />
            {dataset.source_url && (
              <div className="lineage-meta-row">
                <span className="lineage-meta-label">Source Path</span>
                <a className="meta-link" href={dataset.source_url} rel="noreferrer" target="_blank">
                  {dataset.source_dataset_name} ↗
                </a>
              </div>
            )}
          </div>

          {/* Lineage flow */}
          {dataset.lineage.length === 0 ? (
            <p className="doc-text empty" style={{ marginTop: "20px" }}>No lineage recorded.</p>
          ) : (
            <div className="lineage-flows">
              <span className="doc-label" style={{ display: "block", marginBottom: "12px" }}>Pipeline</span>
              {dataset.lineage.map((edge) => (
                <div
                  className="lineage-flow"
                  key={`${edge.lineage_event_type}-${edge.target_dataset_version_id}`}
                >
                  <div className="lineage-node lineage-node--source">
                    <span className="lineage-node-label">Source</span>
                    <strong className="lineage-node-value">
                      {edge.source_dataset_version_id
                        ? `v${edge.source_dataset_version_id}`
                        : edge.source_label}
                    </strong>
                  </div>
                  <div className="lineage-connector">
                    <div className="lineage-connector-badge">{edge.lineage_event_type}</div>
                    <div className="lineage-connector-line">
                      <span className="lineage-arrow-head">›</span>
                    </div>
                  </div>
                  <div className="lineage-node lineage-node--transform">
                    <span className="lineage-node-label">Transform</span>
                    <strong className="lineage-node-value">{edge.transform_name}</strong>
                    <span className="lineage-node-sub">by {edge.created_by_user_id}</span>
                  </div>
                  <div className="lineage-connector">
                    <div className="lineage-connector-line">
                      <span className="lineage-arrow-head">›</span>
                    </div>
                  </div>
                  <div className="lineage-node lineage-node--target">
                    <span className="lineage-node-label">Output</span>
                    <strong className="lineage-node-value">v{edge.target_dataset_version_id}</strong>
                    <span className="lineage-node-sub">this dataset</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {active === "quality" && (
        <div className="tab-panel">
          {/* 1. Score hero */}
          {(() => {
            const qs = dataset.quality_summary;
            return (
              <>
                <div className="qc-hero">
                  <div className="qc-b-top">
                    <div className="qc-b-num">
                      <span style={{ color: scoreColor(qs.score) }}>{qs.score}</span>
                      <span className="qc-b-denom">/100</span>
                    </div>
                    <span className={`qc-b-pill qc-b-pill--${qs.score >= 90 ? "ok" : qs.score >= 60 ? "warn" : "err"}`}>
                      <span className="qc-b-dot" />
                      {qs.score_label}
                    </span>
                  </div>
                  {qs.score_components.length > 0 && (
                    <>
                      <div className="qc-stack">
                        {qs.score_components.map((comp, i) => (
                          <span
                            key={comp.name}
                            style={{ width: `${comp.weight}%`, background: DONUT_COLORS[i % DONUT_COLORS.length] }}
                            title={`${comp.name}: ${comp.weight}%`}
                          />
                        ))}
                      </div>
                      <div className="qc-leg">
                        {qs.score_components.map((comp, i) => {
                          const check = qs.checks.find((c) => c.name === comp.name);
                          return (
                            <div className="qc-leg-row" key={comp.name}>
                              <span className="qc-leg-swatch" style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }} />
                              <span className="qc-leg-name">{comp.name}</span>
                              <span className="qc-leg-weight">{comp.weight}%</span>
                              {check !== undefined && (
                                <span className="qc-leg-val">{formatMetric(check.metric_value)}</span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>

                {/* 2. Checks */}
                {qs.checks.length > 0 && (
                  <div className="qc-section">
                    <span className="qc-section-label">Quality Checks</span>
                    <div className="qc-check-list">
                      {qs.checks.map((check) => (
                        <div
                          className={`qc-check-row${check.status === "review" ? " qc-check-row--review" : ""}`}
                          key={check.metric_name}
                        >
                          <span className={`qc-check-icon qc-icon--${check.status}`}>
                            {check.status === "ok" ? "✓" : check.status === "review" ? "⚠" : "—"}
                          </span>
                          <div className="qc-check-body">
                            <span className="qc-check-name">{check.name}</span>
                            <span className="qc-check-sub">{check.description}</span>
                          </div>
                          <div className="qc-check-right">
                            <span className="qc-check-metric mono">{formatMetric(check.metric_value)}</span>
                            <span className={checkBadgeClass(check.status)}>{check.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 3. Raw metrics */}
                {dataset.quality_metrics.length > 0 && (
                  <div className="qc-section">
                    <span className="qc-section-label">Raw Metrics</span>
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Metric</th>
                            <th>Value</th>
                            <th>Source</th>
                            <th>Recorded</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dataset.quality_metrics.map((m) => (
                            <tr key={m.metric_name}>
                              <td className="mono">{m.metric_name}</td>
                              <td>{formatMetric(m.metric_value)}</td>
                              <td>{m.source_priority}</td>
                              <td>{formatDate(m.timestamp)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* 4. How this score works — toggle at end */}
                <div className="qc-section">
                  <button
                    className="qc-method-btn"
                    onClick={() => setShowMethodology((v) => !v)}
                    aria-expanded={showMethodology}
                  >
                    <span className="qc-info-icon">ⓘ</span>
                    How this score works
                    <span className="qc-method-chevron">{showMethodology ? "▴" : "▾"}</span>
                  </button>
                  {showMethodology && (
                    <div className="qc-method-panel">
                      {/* Score weights as donut chart */}
                      {qs.score_components.length > 0 && (
                        <>
                          <p className="qc-method-section-title">Score weights</p>
                          <DonutChart components={qs.score_components} />
                        </>
                      )}
                      {/* Framework & procedure */}
                      <p className="qc-method-framework">{qs.framework}</p>
                      {qs.procedure.length > 0 && (
                        <>
                          <p className="qc-method-section-title">Measurement steps</p>
                          <ol className="qc-method-steps">
                            {qs.procedure.map((step, i) => <li key={i}>{step}</li>)}
                          </ol>
                        </>
                      )}
                      {qs.null_value_policy && (
                        <p className="qc-method-note">{qs.null_value_policy}</p>
                      )}
                    </div>
                  )}
                </div>
              </>
            );
          })()}
        </div>
      )}
    </div>
  );
}

const DONUT_COLORS = ["#C16E83", "#5C7A4F", "#5B7FA6", "#B5681F", "#7A6B8A"];

function DonutChart({ components }: {
  components: Array<{ name: string; weight: number; description: string }>;
}) {
  const cx = 56, cy = 56, R = 46, r = 28;
  let angle = -Math.PI / 2;

  const slices = components.map((comp, i) => {
    const sweep = (comp.weight / 100) * 2 * Math.PI;
    const start = angle;
    const end = angle + sweep;
    angle = end;
    const cos0 = Math.cos(start), sin0 = Math.sin(start);
    const cos1 = Math.cos(end), sin1 = Math.sin(end);
    const large = sweep > Math.PI ? 1 : 0;
    const d = [
      `M ${(cx + R * cos0).toFixed(2)} ${(cy + R * sin0).toFixed(2)}`,
      `A ${R} ${R} 0 ${large} 1 ${(cx + R * cos1).toFixed(2)} ${(cy + R * sin1).toFixed(2)}`,
      `L ${(cx + r * cos1).toFixed(2)} ${(cy + r * sin1).toFixed(2)}`,
      `A ${r} ${r} 0 ${large} 0 ${(cx + r * cos0).toFixed(2)} ${(cy + r * sin0).toFixed(2)}`,
      "Z",
    ].join(" ");
    return { d, color: DONUT_COLORS[i % DONUT_COLORS.length], ...comp };
  });

  return (
    <div className="qc-donut-wrap">
      <svg viewBox="0 0 112 112" width="112" height="112" style={{ flexShrink: 0 }}>
        {slices.map((s, i) => (
          <path key={i} d={s.d} fill={s.color} stroke="white" strokeWidth="2" />
        ))}
      </svg>
      <div className="qc-donut-legend">
        {slices.map((s, i) => (
          <div className="qc-legend-item" key={i}>
            <span className="qc-legend-dot" style={{ background: s.color }} />
            <span className="qc-legend-name">{s.name}</span>
            <span className="qc-legend-pct">{s.weight}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LineageMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="lineage-meta-row">
      <span className="lineage-meta-label">{label}</span>
      <span className="lineage-meta-value">{value}</span>
    </div>
  );
}

function scoreColor(score: number) {
  if (score >= 90) return "#166534";
  if (score >= 60) return "#92400E";
  return "#9B2C2C";
}

function qualityBadgeClass(score: number) {
  if (score >= 90) return "badge status-active";
  if (score >= 60) return "badge status-paused";
  return "badge danger";
}

function checkBadgeClass(status: string) {
  if (status === "ok") return "badge status-active";
  if (status === "review") return "badge status-paused";
  return "badge neutral";
}

function formatMetric(value: number | undefined) {
  if (value === undefined) return "—";
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
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

