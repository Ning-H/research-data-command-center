import { ArrowRight, BarChart3, ClipboardList, GitBranch, Library } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { getEvaluationSummary, listFailures } from "../../lib/api";

type EvaluationsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function EvaluationsPage({ searchParams = {} }: EvaluationsPageProps) {
  const filters = normalizeFilters(searchParams);
  const [summary, failures] = await Promise.all([
    getEvaluationSummary(filters),
    listFailures({ ...filters, limit: 6 }),
  ]);
  const bestMetric = summary.metric_summary[0];
  const mostRecentRun = summary.runs[0];

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Evaluations</p>
          <h1>Evaluation Loop</h1>
          <p className="subtle">
            Compare model versions with rubric scores, inspect failures, and move the useful
            mistakes into dataset iteration.
          </p>
        </div>
        <div className="action-row">
          <Link className="btn btn--secondary" href="/failure-library">
            Failure library
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
          <span className="badge">API-backed</span>
        </div>
      </div>

      <form className="program-filters" action="/evaluations">
        <input className="filter-input" defaultValue={filters.experiment_id ?? ""} name="experiment_id" placeholder="experiment_id" />
        <input className="filter-input" defaultValue={filters.model_version_id ?? ""} name="model_version_id" placeholder="model_version_id" />
        <input className="filter-input" defaultValue={filters.eval_suite_id ?? ""} name="eval_suite_id" placeholder="eval_suite_id" />
        <button className="btn btn--secondary btn--sm" type="submit">Apply</button>
        <Link className="btn btn--ghost btn--sm" href="/evaluations">Clear</Link>
      </form>

      <div className="summary-grid">
        <Metric label="Eval runs" value={summary.eval_run_count.toLocaleString()} />
        <Metric label="Model versions" value={summary.model_version_count.toLocaleString()} />
        <Metric label="Outputs scored" value={summary.output_count.toLocaleString()} />
        <Metric label="Failures captured" value={summary.failure_count.toLocaleString()} />
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Rubric Movement</h2>
            <p className="subtle">
              Scores stay attached to `model_version_id` so comparisons never float away from the
              checkpoint, run, and dataset version that produced them.
            </p>
          </div>
          {summary.metric_summary.length ? (
            <div className="component-grid">
              {summary.metric_summary.map((metric) => (
                <WorkflowCard icon={<BarChart3 aria-hidden="true" size={18} />} key={metric.metric_name} title={metric.metric_name}>
                  mean {formatScore(metric.mean)} · range {formatScore(metric.min)}-{formatScore(metric.max)} · best model_version_id {metric.best_model_version_id}
                </WorkflowCard>
              ))}
            </div>
          ) : (
            <EmptyState text="No evaluation scores are available for the current filters." />
          )}
        </div>

        <div className="panel">
          <div>
            <h2>Current Best Signal</h2>
            <p className="subtle">
              The first metric summary is a quick handoff into deeper model comparison.
            </p>
          </div>
          {bestMetric ? (
            <div className="record">
              <span className="badge">best by {bestMetric.metric_name}</span>
              <strong>model_version_id {bestMetric.best_model_version_id}</strong>
              <p className="record-text">Best eval_run_id {bestMetric.best_eval_run_id} with max score {formatScore(bestMetric.max)}.</p>
              <Link className="btn btn--secondary btn--sm" href={`/models/${bestMetric.best_model_version_id}`}>
                Open model
                <ArrowRight aria-hidden="true" size={14} />
              </Link>
            </div>
          ) : (
            <EmptyState text="Run the study-material lifecycle script to populate rubric summaries." />
          )}
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Eval Run</th>
              <th>Model</th>
              <th>Lineage</th>
              <th>Scores</th>
              <th>Failures</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {summary.runs.map((run) => (
              <tr key={run.eval_run_id}>
                <td>
                  <strong>eval_run_id {run.eval_run_id}</strong>
                  <div className="muted-row">eval_suite_id {run.eval_suite_id}</div>
                  <div className="muted-row">{run.status}</div>
                </td>
                <td>
                  {run.model_version_name ?? `model_version_id ${run.model_version_id}`}
                  <div className="muted-row">{run.model_name ?? "model family unavailable"}</div>
                </td>
                <td>
                  dataset_id {run.dataset_id}
                  <div className="muted-row">dataset_version_id {run.dataset_version_id}</div>
                  <div className="muted-row">run_id {run.run_id} · checkpoint_id {run.checkpoint_id}</div>
                </td>
                <td>{formatScoreList(run.score_summary)}</td>
                <td>
                  <span className={run.failure_count ? "badge warning" : "badge"}>
                    {run.failure_count} failures
                  </span>
                  <div className="muted-row">{formatFailureTypes(run.failure_types)}</div>
                </td>
                <td>
                  <Link className="btn btn--secondary btn--sm" href={`/failure-library?model_version_id=${run.model_version_id}`}>
                    Failures
                    <ArrowRight aria-hidden="true" size={14} />
                  </Link>
                </td>
              </tr>
            ))}
            {!summary.runs.length ? (
              <tr>
                <td colSpan={6}>
                  <EmptyState text="No eval runs match these filters yet." />
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <div>
          <h2>Recent Failure Handoff</h2>
          <p className="subtle">
            These are the failures ready to inspect, convert into dataset candidates, or route into
            the next dataset version.
          </p>
        </div>
        <div className="record-list">
          {failures.map((failure) => (
            <article className="record" key={failure.eval_failure_id}>
              <span className={failure.severity === "high" ? "badge warning" : "badge neutral"}>{failure.failure_type}</span>
              <strong>{failure.case_name || `eval_failure_id ${failure.eval_failure_id}`}</strong>
              <p className="record-text">{failure.failure_reason}</p>
              <div className="program-kicker">
                <span>model_version_id {failure.model_version_id}</span>
                <span>dataset_id {failure.dataset_id}</span>
                <span>{failure.dataset_candidate_count} candidates</span>
              </div>
              <Link className="btn btn--secondary btn--sm" href={`/failure-library/${failure.eval_failure_id}`}>
                Review failure
                <ArrowRight aria-hidden="true" size={14} />
              </Link>
            </article>
          ))}
          {!failures.length ? <EmptyState text="No failures are available for handoff yet." /> : null}
        </div>
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

function WorkflowCard({
  children,
  icon,
  title,
}: {
  children: ReactNode;
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

function EmptyState({ text }: { text: string }) {
  return <p className="subtle">{text}</p>;
}

function normalizeFilters(searchParams: Record<string, string | string[] | undefined>) {
  return {
    experiment_id: single(searchParams.experiment_id),
    model_version_id: single(searchParams.model_version_id),
    eval_suite_id: single(searchParams.eval_suite_id),
  };
}

function single(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value || undefined;
}

function formatScore(value: number | undefined) {
  if (value === undefined) {
    return "n/a";
  }
  return value.toFixed(3);
}

function formatScoreList(scores: Record<string, { mean: number }>) {
  const entries = Object.entries(scores).slice(0, 3);
  if (!entries.length) {
    return "not scored";
  }
  return entries.map(([name, score]) => `${name} ${formatScore(score.mean)}`).join(" · ");
}

function formatFailureTypes(types: Record<string, number>) {
  const entries = Object.entries(types);
  if (!entries.length) {
    return "no failure types";
  }
  return entries.map(([type, count]) => `${type}: ${count}`).join(" · ");
}
