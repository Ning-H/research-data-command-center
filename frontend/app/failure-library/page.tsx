import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { getFailureLibrarySummary, listFailures } from "../../lib/api";

type FailureLibraryPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function FailureLibraryPage({ searchParams = {} }: FailureLibraryPageProps) {
  const filters = normalizeFilters(searchParams);
  const [summary, failures] = await Promise.all([
    getFailureLibrarySummary(filters),
    listFailures(filters),
  ]);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Failure Library</p>
          <h1>Failure Review Queue</h1>
          <p className="subtle">
            Centralize rubric failures with model, checkpoint, run, and dataset lineage before
            converting useful failures into dataset candidates.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/dataset-iterations">
          Dataset iterations
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <form className="program-filters" action="/failure-library">
        <input className="filter-input" defaultValue={filters.experiment_id ?? ""} name="experiment_id" placeholder="experiment_id" />
        <input className="filter-input" defaultValue={filters.model_version_id ?? ""} name="model_version_id" placeholder="model_version_id" />
        <input className="filter-input" defaultValue={filters.failure_type ?? ""} name="failure_type" placeholder="failure_type" />
        <select className="filter-input" defaultValue={filters.severity ?? ""} name="severity">
          <option value="">Any severity</option>
          <option value="high">high</option>
          <option value="medium">medium</option>
          <option value="low">low</option>
        </select>
        <select className="filter-input" defaultValue={filters.status ?? ""} name="status">
          <option value="">Any status</option>
          <option value="open">open</option>
          <option value="triaged">triaged</option>
          <option value="converted">converted</option>
        </select>
        <button className="btn btn--secondary btn--sm" type="submit">Apply</button>
        <Link className="btn btn--ghost btn--sm" href="/failure-library">Clear</Link>
      </form>

      <div className="summary-grid">
        <Metric label="Failures" value={summary.failure_count.toLocaleString()} />
        <Metric label="Failure types" value={summary.by_failure_type.length.toLocaleString()} />
        <Metric label="Severity bands" value={summary.by_severity.length.toLocaleString()} />
        <Metric label="Statuses" value={summary.by_status.length.toLocaleString()} />
      </div>

      <div className="two-column">
        <Breakdown title="Failure Types" items={summary.by_failure_type} />
        <Breakdown title="Review State" items={summary.by_status} />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Failure</th>
              <th>Model</th>
              <th>Lineage</th>
              <th>Severity</th>
              <th>Candidates</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {failures.map((failure) => (
              <tr key={failure.eval_failure_id}>
                <td>
                  <strong>{failure.case_name || `eval_failure_id ${failure.eval_failure_id}`}</strong>
                  <div className="muted-row mono">eval_failure_id {failure.eval_failure_id}</div>
                  <p className="table-copy">{failure.failure_reason}</p>
                </td>
                <td>
                  {failure.model_version_name ?? `model_version_id ${failure.model_version_id}`}
                  <div className="muted-row">{failure.model_name ?? "model family unavailable"}</div>
                  <div className="muted-row">score {formatScore(failure.score)}</div>
                </td>
                <td>
                  dataset_id {failure.dataset_id}
                  <div className="muted-row">dataset_version_id {failure.dataset_version_id}</div>
                  <div className="muted-row">run_id {failure.run_id} · checkpoint_id {failure.checkpoint_id}</div>
                </td>
                <td>
                  <span className={severityClass(failure.severity)}>{failure.severity}</span>
                  <div className="muted-row">{failure.status}</div>
                  <div className="muted-row">{failure.failure_type}</div>
                </td>
                <td>
                  <span className={failure.dataset_candidate_count ? "badge" : "badge neutral"}>
                    {failure.dataset_candidate_count}
                  </span>
                </td>
                <td>
                  <Link className="btn btn--secondary btn--sm" href={`/failure-library/${failure.eval_failure_id}`}>
                    Review
                    <ArrowRight aria-hidden="true" size={14} />
                  </Link>
                </td>
              </tr>
            ))}
            {!failures.length ? (
              <tr>
                <td colSpan={6}>
                  <p className="subtle">No failures match the current filters.</p>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

function Breakdown({
  items,
  title,
}: {
  items: Array<{ value: string; count: number }>;
  title: string;
}) {
  return (
    <div className="panel">
      <div>
        <h2>{title}</h2>
        <p className="subtle">Grouped from the current failure filters.</p>
      </div>
      <div className="record-list">
        {items.map((item) => (
          <div className="record" key={item.value}>
            <span className="badge neutral">{item.count}</span>
            <strong>{item.value || "unlabeled"}</strong>
          </div>
        ))}
        {!items.length ? <p className="subtle">No grouped data yet.</p> : null}
      </div>
    </div>
  );
}

function normalizeFilters(searchParams: Record<string, string | string[] | undefined>) {
  return {
    experiment_id: single(searchParams.experiment_id),
    model_version_id: single(searchParams.model_version_id),
    failure_type: single(searchParams.failure_type),
    severity: single(searchParams.severity),
    status: single(searchParams.status),
  };
}

function single(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value || undefined;
}

function formatScore(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return value.toFixed(3);
}

function severityClass(severity: string) {
  if (severity === "high") {
    return "badge warning";
  }
  if (severity === "critical") {
    return "badge danger";
  }
  return "badge neutral";
}
