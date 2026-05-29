import { AlertTriangle, ArrowRight, CheckCircle2, Filter, PackagePlus } from "lucide-react";
import Link from "next/link";

import { getFailureLibrarySummary, listFailures, type EvalFailure } from "../../lib/api";

type FailureLibraryPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function FailureLibraryPage({ searchParams = {} }: FailureLibraryPageProps) {
  const filters = normalizeFilters(searchParams);
  const apiFilters = apiFailureFilters(filters);
  const [summary, rawFailures] = await Promise.all([
    getFailureLibrarySummary(apiFilters),
    listFailures({ ...apiFilters, limit: 200 }),
  ]);
  const failures = filterByCandidateState(rawFailures, filters.candidate_state).sort(compareFailurePriority);
  const openFailures = failures.filter((failure) => !isClosedFailure(failure.status));
  const severeOpen = openFailures.filter((failure) => ["critical", "high"].includes(failure.severity));
  const noCandidate = openFailures.filter((failure) => failure.dataset_candidate_count === 0);
  const candidateCreated = failures.filter((failure) => failure.dataset_candidate_count > 0);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Failure Library</p>
          <h1>Failure Review Queue</h1>
          <p className="subtle">
            Triage evaluation failures, validate whether they are real research issues, and move useful
            cases into dataset-candidate review.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/dataset-iterations">
          Dataset iterations
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <form className="filter-grid" action="/failure-library">
        <Filter aria-hidden="true" className="accent-icon" size={18} />
        <label className="filter-field">
          <span>program</span>
          <input className="filter-input" defaultValue={filters.program_id ?? ""} name="program_id" placeholder="Any" />
        </label>
        <label className="filter-field">
          <span>experiment</span>
          <input className="filter-input" defaultValue={filters.experiment_id ?? ""} name="experiment_id" placeholder="Any" />
        </label>
        <label className="filter-field">
          <span>model</span>
          <input className="filter-input" defaultValue={filters.model_version_id ?? ""} name="model_version_id" placeholder="Any" />
        </label>
        <label className="filter-field">
          <span>dataset</span>
          <input className="filter-input" defaultValue={filters.dataset_id ?? ""} name="dataset_id" placeholder="Any" />
        </label>
        <label className="filter-field">
          <span>version</span>
          <input className="filter-input" defaultValue={filters.dataset_version_id ?? ""} name="dataset_version_id" placeholder="Any" />
        </label>
        <label className="filter-field filter-field--wide">
          <span>failure type</span>
          <input className="filter-input" defaultValue={filters.failure_type ?? ""} name="failure_type" placeholder="Any type" />
        </label>
        <label className="filter-field">
          <span>severity</span>
          <select className="filter-input" defaultValue={filters.severity ?? ""} name="severity">
            <option value="">Any</option>
            <option value="critical">critical</option>
            <option value="high">high</option>
            <option value="medium">medium</option>
            <option value="low">low</option>
          </select>
        </label>
        <label className="filter-field">
          <span>status</span>
          <select className="filter-input" defaultValue={filters.status ?? ""} name="status">
            <option value="">Any</option>
            <option value="open">open</option>
            <option value="in_review">in_review</option>
            <option value="valid_failure">valid_failure</option>
            <option value="candidate_created">candidate_created</option>
            <option value="resolved">resolved</option>
            <option value="dismissed">dismissed</option>
          </select>
        </label>
        <label className="filter-field">
          <span>candidate</span>
          <select className="filter-input" defaultValue={filters.candidate_state ?? ""} name="candidate_state">
            <option value="">Any</option>
            <option value="none">No candidate</option>
            <option value="created">Candidate created</option>
          </select>
        </label>
        <div className="filter-actions">
          <button className="btn btn--secondary btn--sm" type="submit">Apply</button>
          <Link className="btn btn--ghost btn--sm" href="/failure-library">Clear</Link>
        </div>
      </form>

      <div className="summary-grid">
        <Metric label="Filtered failures" value={failures.length.toLocaleString()} />
        <Metric label="Severe open" value={severeOpen.length.toLocaleString()} />
        <Metric label="Need candidate" value={noCandidate.length.toLocaleString()} />
        <Metric label="Candidate created" value={candidateCreated.length.toLocaleString()} />
      </div>

      <div className="two-column">
        <Breakdown title="Failure Types" items={summary.by_failure_type} />
        <Breakdown title="Review State" items={summary.by_status} />
      </div>

      <div className="panel panel-heading-row">
        <div>
          <h2>Important Failures First</h2>
          <p className="subtle">
            Rows are ordered by unresolved status, severity, missing candidate, lower score, then recency.
          </p>
        </div>
        <Link className="btn btn--secondary btn--sm" href="/dataset-iterations">
          Review candidates
          <ArrowRight aria-hidden="true" size={14} />
        </Link>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Priority</th>
              <th>Failure</th>
              <th>Evidence</th>
              <th>Source Trace</th>
              <th>Review State</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {failures.map((failure) => (
              <tr key={failure.eval_failure_id}>
                <td>
                  <span className={priorityClass(failure)}>{priorityLabel(failure)}</span>
                  <div className="muted-row">score {formatScore(failure.score)}</div>
                </td>
                <td>
                  <strong>{failure.case_name || `eval_failure_id ${failure.eval_failure_id}`}</strong>
                  <div className="muted-row mono">eval_failure_id {failure.eval_failure_id}</div>
                  <div className="status-stack">
                    <span className={severityClass(failure.severity)}>{failure.severity}</span>
                    <span className="badge neutral">{failure.failure_type}</span>
                  </div>
                </td>
                <td>
                  <p className="table-copy">{failure.failure_reason}</p>
                  {failure.root_cause ? <div className="muted-row">cause: {failure.root_cause}</div> : null}
                </td>
                <td>
                  <strong>{failure.model_version_name ?? `model_version_id ${failure.model_version_id}`}</strong>
                  <div className="muted-row">{failure.model_name ?? "model family unavailable"}</div>
                  <div className="muted-row">
                    dataset {failure.dataset_id} v{failure.dataset_version_id}
                  </div>
                  <div className="muted-row">run {failure.run_id} · checkpoint {failure.checkpoint_id}</div>
                </td>
                <td>
                  <span className={failureStatusClass(failure.status)}>{failure.status}</span>
                  <div className="muted-row">
                    {failure.dataset_candidate_count ? (
                      <>
                        <PackagePlus aria-hidden="true" size={12} /> {failure.dataset_candidate_count} candidate
                      </>
                    ) : (
                      <>
                        <AlertTriangle aria-hidden="true" size={12} /> no candidate
                      </>
                    )}
                  </div>
                  {failure.reviewed_by_user_id ? (
                    <div className="muted-row">reviewed by {failure.reviewed_by_user_id}</div>
                  ) : null}
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
        <p className="subtle">Grouped from the current backend filters.</p>
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
    program_id: single(searchParams.program_id),
    experiment_id: single(searchParams.experiment_id),
    model_version_id: single(searchParams.model_version_id),
    dataset_id: single(searchParams.dataset_id),
    dataset_version_id: single(searchParams.dataset_version_id),
    failure_type: single(searchParams.failure_type),
    severity: single(searchParams.severity),
    status: single(searchParams.status),
    candidate_state: single(searchParams.candidate_state),
  };
}

type FailureFilters = ReturnType<typeof normalizeFilters>;

function apiFailureFilters(filters: FailureFilters): Record<string, string | undefined> {
  return {
    program_id: filters.program_id,
    experiment_id: filters.experiment_id,
    model_version_id: filters.model_version_id,
    dataset_id: filters.dataset_id,
    dataset_version_id: filters.dataset_version_id,
    failure_type: filters.failure_type,
    severity: filters.severity,
    status: filters.status,
  };
}

function filterByCandidateState(failures: EvalFailure[], candidateState?: string) {
  if (candidateState === "none") {
    return failures.filter((failure) => failure.dataset_candidate_count === 0);
  }
  if (candidateState === "created") {
    return failures.filter((failure) => failure.dataset_candidate_count > 0);
  }
  return failures;
}

function single(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value || undefined;
}

function compareFailurePriority(a: EvalFailure, b: EvalFailure) {
  return priorityScore(b) - priorityScore(a);
}

function priorityScore(failure: EvalFailure) {
  const openWeight = isClosedFailure(failure.status) ? 0 : 1000;
  const severityWeight = { critical: 400, high: 300, medium: 160, low: 60 }[failure.severity] ?? 100;
  const candidateWeight = failure.dataset_candidate_count ? 0 : 80;
  const scoreWeight = Math.round((1 - Math.min(Math.max(failure.score ?? 0, 0), 1)) * 100);
  const recencyWeight = Date.parse(failure.created_at || "") / 100000000000 || 0;
  return openWeight + severityWeight + candidateWeight + scoreWeight + recencyWeight;
}

function isClosedFailure(status: string) {
  return ["resolved", "dismissed"].includes(status);
}

function priorityLabel(failure: EvalFailure) {
  if (isClosedFailure(failure.status)) {
    return "closed";
  }
  if (["critical", "high"].includes(failure.severity) && failure.dataset_candidate_count === 0) {
    return "review now";
  }
  if (failure.dataset_candidate_count > 0) {
    return "candidate";
  }
  return "triage";
}

function priorityClass(failure: EvalFailure) {
  const label = priorityLabel(failure);
  if (label === "review now") return "badge danger";
  if (label === "candidate") return "badge status-active";
  if (label === "closed") return "badge neutral";
  return "badge warning";
}

function formatScore(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return value.toFixed(3);
}

function severityClass(severity: string) {
  if (severity === "critical") {
    return "badge danger";
  }
  if (severity === "high") {
    return "badge warning";
  }
  return "badge neutral";
}

function failureStatusClass(status: string) {
  if (status === "resolved" || status === "valid_failure" || status === "candidate_created") {
    return "badge status-active";
  }
  if (status === "dismissed") {
    return "badge neutral";
  }
  if (status === "in_review") {
    return "badge warning";
  }
  return "badge neutral";
}
