import { Activity, ArrowRight, BarChart3, GitBranch, RadioTower } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import type { RunSummary } from "../../lib/api";
import { listRuns } from "../../lib/api";
import RunFilterControls from "./RunFilterControls";

type RunsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

type RunFilters = {
  datasetId: string;
  experimentId: string;
  metricTrend: string;
  programId: string;
  query: string;
  status: string;
};

type RunGroup = {
  key: string;
  programId: number | null;
  experimentId: number | null;
  experimentName: string;
  runs: RunSummary[];
  completed: number;
  failed: number;
  checkpointCount: number;
  averageHealth: number;
  bestFinalLoss: number | null;
};

export default async function RunsPage({ searchParams = {} }: RunsPageProps) {
  const runs = await listRuns();
  const sortedRuns = [...runs].sort((left, right) => timestamp(right.started_at) - timestamp(left.started_at));
  const filters = normalizeRunFilters(searchParams);
  const filteredRuns = applyRunFilters(sortedRuns, filters);
  const completedRuns = runs.filter((run) => run.status === "completed").length;
  const activeRuns = runs.filter((run) => run.status === "running").length;
  const failedRuns = runs.filter((run) => run.status === "failed" || run.status === "killed").length;
  const checkpointCount = runs.reduce((sum, run) => sum + run.checkpoint_count, 0);
  const averageHealth = average(runs.map((run) => run.health_summary.health_score));
  const improvedRuns = runs.filter((run) => (run.metric_summary?.loss_delta_percent ?? 0) < 0).length;
  const regressedRuns = runs.filter((run) => (run.metric_summary?.loss_delta_percent ?? 0) > 0).length;
  const bestRun = lowestBy(
    runs.filter((run) => run.metric_summary?.final_loss !== undefined && run.status === "completed"),
    (run) => run.metric_summary?.final_loss ?? Number.POSITIVE_INFINITY,
  );
  const reviewRun = lowestBy(runs, (run) => run.health_summary.health_score);
  const groups = groupRuns(filteredRuns);
  const filterOptions = buildFilterOptions(runs);
  const activeFilterCount = countActiveFilters(filters);

  return (
    <section className="page runs-console-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Training Runs & Checkpoints</p>
          <h1>Run and Checkpoint Analysis</h1>
          <p className="subtle">
            Read-only metrics, checkpoint, and lineage analysis for runs submitted by training
            scripts through the API or SDK. The UI stays focused on analysis, not job creation.
          </p>
        </div>
        <div className="action-row">
          <Link className="btn btn--secondary" href="/runs/checkpoints">
            Checkpoint ranking
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
          <span className="badge neutral">SDK / API ingest only</span>
        </div>
      </div>

      <div className="summary-grid run-summary-grid">
        <Metric label="Matching runs" value={filteredRuns.length.toLocaleString()} detail={`${runs.length} ingested`} />
        <Metric label="Completed" value={completedRuns.toLocaleString()} detail={`${failedRuns} need review`} />
        <Metric label="Avg health" value={`${averageHealth}/100`} detail={`${improvedRuns} improved loss`} />
        <Metric label="Checkpoints" value={checkpointCount.toLocaleString()} detail="metadata tracked" />
      </div>

      <div className="two-column runs-overview-grid">
        <div className="panel run-health-panel">
          <div className="panel-heading-row">
            <div>
              <h2>Program + Experiment Pulse</h2>
              <p className="subtle">
                Grouped from actual run records so the page expands automatically as new runs arrive.
              </p>
            </div>
            <BarChart3 aria-hidden="true" className="accent-icon" size={20} />
          </div>
          {groups.length ? (
            <div className="run-group-list">
              {groups.map((group) => (
                <article className="run-group-card" key={group.key}>
                  <div>
                    <span className="run-group-kicker">program {group.programId ?? "unlinked"}</span>
                    <h3>{group.experimentName}</h3>
                    <p className="muted-row">
                      experiment {group.experimentId ?? "unlinked"} · {group.runs.length} runs ·{" "}
                      {group.checkpointCount} checkpoints
                    </p>
                  </div>
                  <div className="run-group-stats">
                    <StatPill label="completed" value={group.completed} tone="success" />
                    <StatPill label="failed" value={group.failed} tone={group.failed ? "warn" : "neutral"} />
                    <StatPill label="health" value={`${group.averageHealth}/100`} />
                    <StatPill
                      label="best loss"
                      value={group.bestFinalLoss === null ? "n/a" : formatMetric(group.bestFinalLoss)}
                    />
                  </div>
                  <RunMarkerStrip runs={group.runs} />
                </article>
              ))}
            </div>
          ) : (
            <EmptyState text="No training runs have been ingested yet. Run records will appear here after SDK/API submission." />
          )}
        </div>

        <div className="panel run-insight-panel">
          <div className="panel-heading-row">
            <div>
              <h2>Quick Read</h2>
              <p className="subtle">Current status from the latest ingested run set.</p>
            </div>
            <Activity aria-hidden="true" className="accent-icon" size={20} />
          </div>
          <div className="status-stack">
            <StatusBar label="completed" count={completedRuns} total={runs.length} tone="success" />
            <StatusBar label="running" count={activeRuns} total={runs.length} />
            <StatusBar label="failed or killed" count={failedRuns} total={runs.length} tone="warn" />
            <StatusBar label="loss improved" count={improvedRuns} total={runs.length} tone="success" />
            <StatusBar label="loss regressed" count={regressedRuns} total={runs.length} tone="warn" />
          </div>
          <div className="insight-card-grid">
            <InsightCard
              icon={<RadioTower aria-hidden="true" size={17} />}
              label="Latest run"
              title={sortedRuns[0]?.run_name ?? "No runs yet"}
              detail={sortedRuns[0] ? formatDateTime(sortedRuns[0].started_at) : "Waiting for SDK/API ingestion"}
              href={sortedRuns[0] ? `/runs/${sortedRuns[0].run_id}` : undefined}
            />
            <InsightCard
              icon={<BarChart3 aria-hidden="true" size={17} />}
              label="Best completed loss"
              title={bestRun ? formatMetric(bestRun.metric_summary?.final_loss) : "n/a"}
              detail={bestRun?.run_name ?? "No completed run with loss yet"}
              href={bestRun ? `/runs/${bestRun.run_id}` : undefined}
            />
            <InsightCard
              icon={<GitBranch aria-hidden="true" size={17} />}
              label="Needs inspection"
              title={reviewRun ? `${reviewRun.health_summary.health_score}/100` : "n/a"}
              detail={reviewRun?.run_name ?? "No health signals yet"}
              href={reviewRun ? `/runs/${reviewRun.run_id}` : undefined}
            />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-heading-row">
          <div>
            <h2>Run Records</h2>
            <p className="subtle">
              Every row is produced from backend run records, metric summaries, checkpoint metadata,
              and health signals.
            </p>
          </div>
          <span className="badge neutral">
            {activeFilterCount ? `${activeFilterCount} filters` : "All runs"}
          </span>
        </div>
        <RunFilterControls filters={filters} options={filterOptions} />
        <div className="table-wrap run-table-wrap">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Program / Experiment</th>
                <th>Dataset</th>
                <th>Status</th>
                <th>Metric Movement</th>
                <th>Health</th>
                <th>Checkpoints</th>
                <th>Ingest Source</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => (
                <tr key={run.run_id}>
                  <td>
                    <strong>{run.run_name}</strong>
                    <div className="muted-row mono">run_id {run.run_id}</div>
                    <div className="muted-row">{formatDateTime(run.started_at)}</div>
                  </td>
                  <td>
                    program {run.program_id ?? "unlinked"}
                    <div className="muted-row">{run.experiment_name}</div>
                    <div className="muted-row">experiment {run.experiment_id ?? "unlinked"}</div>
                  </td>
                  <td>
                    dataset {run.dataset_id}
                    <div className="muted-row">version {run.dataset_version_id}</div>
                  </td>
                  <td>
                    <span className={statusBadgeClass(run.status)}>{run.status}</span>
                  </td>
                  <td>
                    <MetricMovement run={run} />
                  </td>
                  <td>
                    <strong>{run.health_summary.health_score}/100</strong>
                    <div className="muted-row">{run.health_summary.health_label}</div>
                  </td>
                  <td>{run.checkpoint_count}</td>
                  <td>
                    {run.ingest_source}
                    <div className="muted-row">{run.source_priority}</div>
                  </td>
                  <td>
                    <Link className="btn btn--secondary btn--sm" href={`/runs/${run.run_id}`}>
                      Analyze
                      <ArrowRight aria-hidden="true" size={14} />
                    </Link>
                  </td>
                </tr>
              ))}
              {!filteredRuns.length ? (
                <tr>
                  <td colSpan={9}>
                    <EmptyState text="No run records match the current filters." />
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-label">{detail}</p>
    </div>
  );
}

function StatPill({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  tone?: "neutral" | "warn" | "success";
}) {
  const toneClass = tone === "warn" ? "run-stat-pill--warn" : tone === "success" ? "run-stat-pill--success" : "";
  return (
    <span className={toneClass ? `run-stat-pill ${toneClass}` : "run-stat-pill"}>
      <strong>{value}</strong>
      {label}
    </span>
  );
}

function StatusBar({
  label,
  count,
  total,
  tone = "neutral",
}: {
  label: string;
  count: number;
  total: number;
  tone?: "neutral" | "warn" | "success";
}) {
  const percent = total ? Math.round((count / total) * 100) : 0;
  return (
    <div className="status-bar-row">
      <div className="status-bar-label">
        <span>{label}</span>
        <strong>{count}</strong>
      </div>
      <div className="status-bar-track" aria-label={`${label}: ${percent}%`}>
        <span className={`status-bar-fill status-bar-fill--${tone}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function InsightCard({
  detail,
  href,
  icon,
  label,
  title,
}: {
  detail: string;
  href?: string;
  icon: ReactNode;
  label: string;
  title: string;
}) {
  const content = (
    <>
      <span className="insight-icon">{icon}</span>
      <span className="run-group-kicker">{label}</span>
      <strong>{title}</strong>
      <span>{detail}</span>
    </>
  );
  if (!href) {
    return <div className="insight-card">{content}</div>;
  }
  return (
    <Link className="insight-card insight-card--link" href={href}>
      {content}
    </Link>
  );
}

function RunMarkerStrip({ runs }: { runs: RunSummary[] }) {
  return (
    <div className="run-marker-section">
      <div className="run-marker-head">
        <span>Runs in this experiment</span>
        <span>Click a marker to inspect</span>
      </div>
      <div className="run-marker-strip" aria-label="Runs in this experiment">
        {runs.map((run) => (
          <Link
            aria-label={`${run.run_name}, ${run.status}, health ${run.health_summary.health_score} of 100`}
            className={`run-marker run-marker--${statusTone(run.status, run.health_summary.health_score)}`}
            href={`/runs/${run.run_id}`}
            key={run.run_id}
            title={`${run.run_name}: ${run.status}, health ${run.health_summary.health_score}/100`}
          >
            <span className="run-marker-dot" aria-hidden="true" />
            <span className="run-marker-id">#{run.run_id}</span>
            <span className="run-marker-score">{run.health_summary.health_score}</span>
            <span className="run-marker-tooltip">
              {run.status} · {formatMetric(run.metric_summary?.final_loss)} final loss · {run.checkpoint_count} checkpoints
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

function statusTone(status: string, healthScore: number) {
  if (status === "failed" || status === "killed" || healthScore < 60) {
    return "warn";
  }
  if (status === "running") {
    return "active";
  }
  return "complete";
}

function MetricMovement({ run }: { run: RunSummary }) {
  const { final_loss: finalLoss, initial_loss: initialLoss, loss_delta_percent: delta } = run.metric_summary ?? {};
  if (finalLoss === undefined || initialLoss === undefined || delta === undefined) {
    return <span className="muted-row">no loss metrics</span>;
  }
  const improved = delta < 0;
  return (
    <div className="metric-movement">
      <strong>{formatMetric(finalLoss)}</strong>
      <span className={improved ? "metric-delta metric-delta--good" : "metric-delta metric-delta--warn"}>
        {improved ? "" : "+"}
        {delta.toFixed(1)}%
      </span>
      <div className="muted-row">
        {formatMetric(initialLoss)} {"->"} {formatMetric(finalLoss)}
      </div>
    </div>
  );
}

function groupRuns(runs: RunSummary[]): RunGroup[] {
  const groups = new Map<string, RunSummary[]>();
  for (const run of runs) {
    const key = `${run.program_id ?? "none"}-${run.experiment_id ?? "none"}-${run.experiment_name}`;
    groups.set(key, [...(groups.get(key) ?? []), run]);
  }
  return [...groups.entries()].map(([key, groupRunsForKey]) => {
    const withLoss = groupRunsForKey
      .map((run) => run.metric_summary?.final_loss)
      .filter((value): value is number => value !== undefined);
    return {
      key,
      programId: groupRunsForKey[0].program_id ?? null,
      experimentId: groupRunsForKey[0].experiment_id ?? null,
      experimentName: groupRunsForKey[0].experiment_name,
      runs: groupRunsForKey,
      completed: groupRunsForKey.filter((run) => run.status === "completed").length,
      failed: groupRunsForKey.filter((run) => run.status === "failed" || run.status === "killed").length,
      checkpointCount: groupRunsForKey.reduce((sum, run) => sum + run.checkpoint_count, 0),
      averageHealth: average(groupRunsForKey.map((run) => run.health_summary.health_score)),
      bestFinalLoss: withLoss.length ? Math.min(...withLoss) : null,
    };
  });
}

function normalizeRunFilters(searchParams: Record<string, string | string[] | undefined>): RunFilters {
  return {
    datasetId: first(searchParams.dataset_id) ?? "",
    experimentId: first(searchParams.experiment_id) ?? "",
    metricTrend: first(searchParams.metric_trend) ?? "",
    programId: first(searchParams.program_id) ?? "",
    query: first(searchParams.q) ?? "",
    status: first(searchParams.status) ?? "",
  };
}

function applyRunFilters(runs: RunSummary[], filters: RunFilters) {
  const query = filters.query.trim().toLowerCase();
  return runs.filter((run) => {
    if (filters.programId && entityValue(run.program_id) !== filters.programId) {
      return false;
    }
    if (filters.experimentId && entityValue(run.experiment_id) !== filters.experimentId) {
      return false;
    }
    if (filters.status && run.status !== filters.status) {
      return false;
    }
    if (filters.datasetId && String(run.dataset_id) !== filters.datasetId) {
      return false;
    }
    if (filters.metricTrend) {
      const delta = run.metric_summary?.loss_delta_percent;
      if (filters.metricTrend === "improved" && !(delta !== undefined && delta < 0)) {
        return false;
      }
      if (filters.metricTrend === "regressed" && !(delta !== undefined && delta > 0)) {
        return false;
      }
      if (filters.metricTrend === "missing" && delta !== undefined) {
        return false;
      }
    }
    if (query && !runSearchText(run).includes(query)) {
      return false;
    }
    return true;
  });
}

function buildFilterOptions(runs: RunSummary[]) {
  return {
    datasets: uniqueOptions(
      runs.map((run) => ({
        label: `dataset ${run.dataset_id}`,
        value: String(run.dataset_id),
      })),
    ),
    experiments: uniqueOptions(
      runs.map((run) => ({
        label: run.experiment_id === null || run.experiment_id === undefined
          ? "Unlinked experiment"
          : `${run.experiment_name} (experiment ${run.experiment_id})`,
        value: entityValue(run.experiment_id),
      })),
    ),
    programs: uniqueOptions(
      runs.map((run) => ({
        label: run.program_id === null || run.program_id === undefined ? "Unlinked program" : `Program ${run.program_id}`,
        value: entityValue(run.program_id),
      })),
    ),
    statuses: [...new Set(runs.map((run) => run.status))].sort(),
  };
}

function uniqueOptions(options: Array<{ label: string; value: string }>) {
  const seen = new Map<string, string>();
  for (const option of options) {
    if (!seen.has(option.value)) {
      seen.set(option.value, option.label);
    }
  }
  return [...seen.entries()]
    .map(([value, label]) => ({ label, value }))
    .sort((left, right) => left.label.localeCompare(right.label));
}

function entityValue(value: number | null | undefined) {
  return value === null || value === undefined ? "unlinked" : String(value);
}

function runSearchText(run: RunSummary) {
  return [
    run.run_name,
    run.experiment_name,
    run.model_family,
    run.ingest_source,
    run.training_environment,
    run.source_priority,
    String(run.run_id),
  ]
    .join(" ")
    .toLowerCase();
}

function countActiveFilters(filters: RunFilters) {
  return Object.values(filters).filter((value) => value.trim() !== "").length;
}

function statusBadgeClass(status: string) {
  if (status === "failed" || status === "killed") {
    return "badge warning";
  }
  if (status === "running") {
    return "badge status-active";
  }
  if (status === "completed") {
    return "badge status-completed";
  }
  return "badge";
}

function EmptyState({ text }: { text: string }) {
  return <p className="subtle">{text}</p>;
}

function average(values: number[]) {
  if (!values.length) {
    return 0;
  }
  return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
}

function lowestBy<T>(items: T[], selector: (item: T) => number): T | undefined {
  return items.reduce<T | undefined>((best, item) => {
    if (!best || selector(item) < selector(best)) {
      return item;
    }
    return best;
  }, undefined);
}

function timestamp(value: string) {
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function formatMetric(value: number | undefined) {
  if (value === undefined) {
    return "n/a";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
}

function formatDateTime(value: string) {
  if (!value) {
    return "not available";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
