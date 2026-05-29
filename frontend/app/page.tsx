import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  BrainCircuit,
  ClipboardCheck,
  Clock3,
  Database,
  FlaskConical,
  LineChart,
  ListChecks,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import {
  listDatasetCandidates,
  listDatasets,
  listEvalRuns,
  listExperiments,
  listFailures,
  listModels,
  listResearchPrograms,
  listRuns,
  type DatasetCandidate,
  type DatasetSummary,
  type EvalFailure,
  type EvalRunSummary,
  type ExperimentSummary,
  type ModelVersionSummary,
  type ResearchProgramSummary,
  type RunSummary,
} from "../lib/api";

export const dynamic = "force-dynamic";

const CURRENT_RESEARCHER_NAME = process.env.NEXT_PUBLIC_RESEARCHER_NAME ?? "Lena Keys";
const CURRENT_USER_ID = process.env.NEXT_PUBLIC_USER_ID ?? CURRENT_RESEARCHER_NAME;

type ActivityItem = {
  badge: string;
  detail: string;
  href: string;
  icon: ReactNode;
  timestamp: string;
  title: string;
};

type AttentionItem = {
  count: number;
  detail: string;
  href: string;
  label: string;
  tone: "danger" | "warning" | "neutral";
};

export default async function HomePage() {
  const [programs, experiments, datasets, runs, models, evalRuns, failures, candidates] =
    await Promise.all([
      listResearchPrograms({}),
      listExperiments({}),
      listDatasets(),
      listRuns(),
      listModels(),
      listEvalRuns({}),
      listFailures({}),
      listDatasetCandidates({}),
    ]);

  const userContext = {
    researcherName: CURRENT_RESEARCHER_NAME,
    userId: CURRENT_USER_ID,
  };

  const myPrograms = programs.filter((program) => isMyProgram(program, userContext));
  const myProgramIds = new Set(myPrograms.map((program) => program.program_id));
  const myExperiments = experiments.filter(
    (experiment) => isMyExperiment(experiment, myProgramIds, userContext),
  );
  const myExperimentIds = new Set(myExperiments.map((experiment) => experiment.experiment_id));
  const myRuns = runs.filter((run) => isMyRun(run, myProgramIds, myExperimentIds, userContext));
  const myModels = models.filter((model) =>
    isMyModel(model, myProgramIds, myExperimentIds, userContext),
  );
  const myDatasetRefs = collectDatasetRefs(myPrograms, myExperiments, myRuns, myModels);
  const myDatasets = datasets.filter((dataset) =>
    myDatasetRefs.has(datasetRefKey(dataset.dataset_id, dataset.dataset_version_id)),
  );

  const pendingCandidates = candidates.filter((candidate) =>
    ["pending", "proposed", "needs_review", "review"].includes(normalize(candidate.status)),
  );
  const unresolvedFailures = failures.filter((failure) => normalize(failure.status) !== "resolved");
  const highSeverityFailures = unresolvedFailures.filter((failure) =>
    ["high", "critical"].includes(normalize(failure.severity)),
  );
  const failedRuns = runs.filter((run) => normalize(run.status) === "failed");
  const latestActivity = buildLatestActivity({
    candidates,
    datasets,
    evalRuns,
    experiments,
    failures,
    models,
    programs,
    runs,
  });
  const attentionItems: AttentionItem[] = [
    {
      count: highSeverityFailures.length,
      detail: "High-severity eval failures that can become corrected training examples.",
      href: "/failure-library?severity=high",
      label: "High-severity failures",
      tone: highSeverityFailures.length ? "danger" : "neutral",
    },
    {
      count: pendingCandidates.length,
      detail: "Proposed dataset candidates waiting for review or inclusion.",
      href: "/dataset-iterations",
      label: "Dataset candidates",
      tone: pendingCandidates.length ? "warning" : "neutral",
    },
    {
      count: failedRuns.length,
      detail: "Training runs that did not complete and may need rerun context.",
      href: "/training-runs",
      label: "Failed runs",
      tone: failedRuns.length ? "danger" : "neutral",
    },
  ];

  return (
    <section className="page home-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Home</p>
          <h1>Latest research changes and your assets.</h1>
          <p className="subtle">
            Signed in as {CURRENT_RESEARCHER_NAME}. Tracking recent programs, datasets, runs,
            checkpoints, models, evals, and failure-driven data work.
          </p>
        </div>
        <div className="home-user-chip">
          <UserRound aria-hidden="true" size={17} />
          <span>{CURRENT_USER_ID}</span>
        </div>
      </div>

      <div className="summary-grid">
        <Metric label="My programs" value={myPrograms.length} />
        <Metric label="My experiments" value={myExperiments.length} />
        <Metric label="My runs / models" value={`${myRuns.length} / ${myModels.length}`} />
        <Metric label="Open failures" value={unresolvedFailures.length} />
      </div>

      <div className="home-hero-grid">
        <section className="panel home-feed-panel">
          <div className="panel-heading-row">
            <div>
              <h2>Latest Changes</h2>
              <p className="subtle">The newest research objects across the command center.</p>
            </div>
            <Link className="btn btn--secondary btn--sm" href="/research-programs">
              Browse all
              <ArrowRight aria-hidden="true" size={15} />
            </Link>
          </div>
          <div className="home-feed">
            {latestActivity.map((item) => (
              <Link className="home-feed-item" href={item.href} key={`${item.badge}-${item.href}`}>
                <span className="home-feed-icon">{item.icon}</span>
                <span className="home-feed-body">
                  <span className="home-feed-topline">
                    <span className="badge neutral">{item.badge}</span>
                    <span className="muted-row">{formatDateTime(item.timestamp)}</span>
                  </span>
                  <strong>{item.title}</strong>
                  <span className="subtle">{item.detail}</span>
                </span>
                <ArrowRight aria-hidden="true" className="home-feed-arrow" size={16} />
              </Link>
            ))}
            {!latestActivity.length && (
              <div className="empty-state">
                <Clock3 aria-hidden="true" size={18} />
                <p>No recent research activity is available yet.</p>
              </div>
            )}
          </div>
        </section>

        <section className="panel">
          <div>
            <h2>Needs Attention</h2>
            <p className="subtle">The work a researcher usually wants surfaced before browsing.</p>
          </div>
          <div className="attention-list">
            {attentionItems.map((item) => (
              <Link className={`attention-item attention-item--${item.tone}`} href={item.href} key={item.label}>
                <span>
                  <strong>{item.count}</strong>
                  <span>{item.label}</span>
                </span>
                <p>{item.detail}</p>
              </Link>
            ))}
          </div>
        </section>
      </div>

      <section className="panel">
        <div className="panel-heading-row">
          <div>
            <h2>My Research Assets</h2>
            <p className="subtle">
              Assets connected to {CURRENT_RESEARCHER_NAME} or the local user id {CURRENT_USER_ID}.
            </p>
          </div>
          <Link className="btn btn--secondary btn--sm" href="/settings">
            Settings
            <ArrowRight aria-hidden="true" size={15} />
          </Link>
        </div>
        <div className="asset-grid">
          <AssetCard
            count={myPrograms.length}
            emptyText="No owned programs found."
            href="/research-programs"
            icon={<BrainCircuit aria-hidden="true" size={19} />}
            items={myPrograms.map((program) => program.program_name)}
            label="Programs"
          />
          <AssetCard
            count={myExperiments.length}
            emptyText="No attached experiments found."
            href="/experiments"
            icon={<FlaskConical aria-hidden="true" size={19} />}
            items={myExperiments.map((experiment) => experiment.experiment_name)}
            label="Experiments"
          />
          <AssetCard
            count={myDatasets.length}
            emptyText="No linked dataset versions yet."
            href="/datasets"
            icon={<Database aria-hidden="true" size={19} />}
            items={myDatasets.map(
              (dataset) => `${dataset.name} v${dataset.dataset_version_id}`,
            )}
            label="Dataset versions"
          />
          <AssetCard
            count={myRuns.length}
            emptyText="No submitted runs found."
            href="/training-runs"
            icon={<LineChart aria-hidden="true" size={19} />}
            items={myRuns.map((run) => run.run_name)}
            label="Runs"
          />
          <AssetCard
            count={myModels.length}
            emptyText="No promoted models found."
            href="/models"
            icon={<Boxes aria-hidden="true" size={19} />}
            items={myModels.map((model) => model.model_version_name || model.model_name)}
            label="Models"
          />
          <AssetCard
            count={pendingCandidates.length}
            emptyText="No candidate-review queue yet."
            href="/dataset-iterations"
            icon={<ListChecks aria-hidden="true" size={19} />}
            items={pendingCandidates.map((candidate) => candidate.proposed_input_text)}
            label="Candidate queue"
          />
        </div>
      </section>

      <div className="two-column">
        <section className="panel">
          <div>
            <h2>Recent Eval Signals</h2>
            <p className="subtle">Last eval runs and failures, with direct paths into review.</p>
          </div>
          <div className="record-list">
            {sortByTime(evalRuns, (run) => run.ended_at || run.started_at)
              .slice(0, 3)
              .map((run) => (
                <Link className="record record-link" href="/evaluations" key={run.eval_run_id}>
                  <span className={statusBadgeClass(run.status)}>{run.status}</span>
                  <h3>{run.model_name || `Model version ${run.model_version_id}`}</h3>
                  <p className="subtle">
                    {evalRunDetail(run)}, overall{" "}
                    {formatScore(run.score_summary?.overall?.mean)}
                  </p>
                </Link>
              ))}
            {!evalRuns.length && <p className="subtle">No eval runs have been registered yet.</p>}
          </div>
        </section>

        <section className="panel">
          <div>
            <h2>Latest Data Movement</h2>
            <p className="subtle">Recent dataset versions and failure-derived candidate work.</p>
          </div>
          <div className="metadata-grid single-column">
            <Metadata label="registered dataset versions" value={datasets.length} />
            <Metadata label="candidate records" value={candidates.length} />
            <Metadata label="included candidates" value={candidates.filter((c) => c.included_dataset_version_id).length} />
            <Metadata label="latest dataset update" value={formatDateTime(latestTimestamp(datasets, (d) => d.last_updated_date || d.created_at))} />
          </div>
        </section>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

function AssetCard({
  count,
  emptyText,
  href,
  icon,
  items,
  label,
}: {
  count: number;
  emptyText: string;
  href: string;
  icon: ReactNode;
  items: string[];
  label: string;
}) {
  const topItems = items.filter(Boolean).slice(0, 3);
  return (
    <Link className="asset-card" href={href}>
      <span className="asset-card-heading">
        <span className="asset-card-icon">{icon}</span>
        <span>{label}</span>
        <strong>{count}</strong>
      </span>
      <span className="asset-card-list">
        {topItems.map((item) => (
          <span key={item}>{truncate(item, 72)}</span>
        ))}
        {!topItems.length && <span>{emptyText}</span>}
      </span>
    </Link>
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

function buildLatestActivity({
  candidates,
  datasets,
  evalRuns,
  experiments,
  failures,
  models,
  programs,
  runs,
}: {
  candidates: DatasetCandidate[];
  datasets: DatasetSummary[];
  evalRuns: EvalRunSummary[];
  experiments: ExperimentSummary[];
  failures: EvalFailure[];
  models: ModelVersionSummary[];
  programs: ResearchProgramSummary[];
  runs: RunSummary[];
}): ActivityItem[] {
  const items: ActivityItem[] = [
    ...programs.map((program) => ({
      badge: "Program",
      detail: program.current_focus || program.research_goal || program.status,
      href: `/research-programs/${program.program_id}`,
      icon: <BrainCircuit aria-hidden="true" size={18} />,
      timestamp: program.updated_at || program.created_at,
      title: program.program_name,
    })),
    ...experiments.map((experiment) => ({
      badge: "Experiment",
      detail: experiment.research_question || experiment.hypothesis || experiment.status,
      href: `/experiments/${experiment.experiment_id}`,
      icon: <FlaskConical aria-hidden="true" size={18} />,
      timestamp: experiment.updated_at || experiment.created_at,
      title: experiment.experiment_name,
    })),
    ...datasets.map((dataset) => ({
      badge: "Dataset",
      detail: `${dataset.record_count.toLocaleString()} records · ${dataset.quality_label || dataset.source_label}`,
      href: `/datasets/${dataset.dataset_id}`,
      icon: <Database aria-hidden="true" size={18} />,
      timestamp: dataset.last_updated_date || dataset.created_at || dataset.registration_date,
      title: `${dataset.name} v${dataset.dataset_version_id}`,
    })),
    ...runs.map((run) => ({
      badge: "Run",
      detail: `${run.status} · ${run.checkpoint_count} checkpoints · ${run.model_family}`,
      href: `/runs/${run.run_id}`,
      icon: <LineChart aria-hidden="true" size={18} />,
      timestamp: run.ended_at || run.started_at,
      title: run.run_name,
    })),
    ...models.map((model) => ({
      badge: "Model",
      detail: `${model.status} · checkpoint ${model.checkpoint_id}`,
      href: `/models/${model.model_version_id}`,
      icon: <Boxes aria-hidden="true" size={18} />,
      timestamp: model.created_at,
      title: model.model_version_name || model.model_name,
    })),
    ...evalRuns.map((run) => ({
      badge: "Eval",
      detail: evalRunDetail(run),
      href: "/evaluations",
      icon: <ClipboardCheck aria-hidden="true" size={18} />,
      timestamp: run.ended_at || run.started_at,
      title: run.model_name || `Model version ${run.model_version_id}`,
    })),
    ...failures.map((failure) => ({
      badge: "Failure",
      detail: `${failure.severity} · ${failure.failure_reason}`,
      href: `/failure-library/${failure.eval_failure_id}`,
      icon: <AlertTriangle aria-hidden="true" size={18} />,
      timestamp: failure.created_at,
      title: failure.failure_type.replaceAll("_", " "),
    })),
    ...candidates.map((candidate) => ({
      badge: "Candidate",
      detail: `${candidate.status} · ${candidate.failure_type.replaceAll("_", " ")}`,
      href: "/dataset-iterations",
      icon: <ListChecks aria-hidden="true" size={18} />,
      timestamp: candidate.included_at || candidate.reviewed_at || candidate.created_at,
      title: candidate.proposed_input_text,
    })),
  ];

  return sortByTime(items, (item) => item.timestamp).slice(0, 8);
}

function isMyProgram(
  program: ResearchProgramSummary,
  user: { researcherName: string; userId: string },
) {
  return (
    matchesIdentity(program.owner_name, user) ||
    matchesIdentity(program.created_by_user_id, user) ||
    matchesIdentity(program.updated_by_user_id, user) ||
    program.researcher_names.some((name) => matchesIdentity(name, user)) ||
    program.notes.some((note) => matchesIdentity(note.author_name, user))
  );
}

function isMyExperiment(
  experiment: ExperimentSummary,
  myProgramIds: Set<number>,
  user: { researcherName: string; userId: string },
) {
  return (
    myProgramIds.has(experiment.program_id) ||
    matchesIdentity(experiment.owner_name, user) ||
    matchesIdentity(experiment.created_by_user_id, user) ||
    matchesIdentity(experiment.updated_by_user_id, user) ||
    experiment.notes.some((note) => matchesIdentity(note.author_name, user))
  );
}

function isMyRun(
  run: RunSummary,
  myProgramIds: Set<number>,
  myExperimentIds: Set<number>,
  user: { researcherName: string; userId: string },
) {
  return (
    matchesIdentity(run.created_by_user_id, user) ||
    (typeof run.program_id === "number" && myProgramIds.has(run.program_id)) ||
    (typeof run.experiment_id === "number" && myExperimentIds.has(run.experiment_id))
  );
}

function isMyModel(
  model: ModelVersionSummary,
  myProgramIds: Set<number>,
  myExperimentIds: Set<number>,
  user: { researcherName: string; userId: string },
) {
  return (
    matchesIdentity(model.created_by_user_id, user) ||
    myProgramIds.has(model.program_id) ||
    myExperimentIds.has(model.experiment_id)
  );
}

function collectDatasetRefs(
  programs: ResearchProgramSummary[],
  experiments: ExperimentSummary[],
  runs: RunSummary[],
  models: ModelVersionSummary[],
) {
  const refs = new Set<string>();

  for (const program of programs) {
    for (const ref of program.linked_datasets ?? program.linked_dataset_versions ?? []) {
      refs.add(datasetRefKey(ref.dataset_id, ref.dataset_version_id));
    }
  }
  for (const experiment of experiments) {
    for (const ref of experiment.linked_datasets) {
      refs.add(datasetRefKey(ref.dataset_id, ref.dataset_version_id));
    }
  }
  for (const run of runs) {
    refs.add(datasetRefKey(run.dataset_id, run.dataset_version_id));
  }
  for (const model of models) {
    refs.add(datasetRefKey(model.dataset_id, model.dataset_version_id));
  }

  return refs;
}

function datasetRefKey(datasetId: number, datasetVersionId: number) {
  return `${datasetId}:${datasetVersionId}`;
}

function matchesIdentity(value: string | undefined | null, user: { researcherName: string; userId: string }) {
  const normalizedValue = normalize(value);
  if (!normalizedValue) return false;
  return normalizedValue === normalize(user.researcherName) || normalizedValue === normalize(user.userId);
}

function normalize(value: string | undefined | null) {
  return String(value ?? "").trim().toLowerCase();
}

function statusBadgeClass(status: string) {
  const map: Record<string, string> = {
    active: "badge status-active",
    archived: "badge status-archived",
    completed: "badge status-completed",
    failed: "badge danger",
    planning: "badge status-planning",
    promoted: "badge status-active",
    registered: "badge status-active",
    running: "badge status-active",
  };
  return map[normalize(status)] ?? "badge neutral";
}

function sortByTime<T>(items: T[], getTimestamp: (item: T) => string | undefined | null) {
  return [...items].sort((a, b) => parseTimestamp(getTimestamp(b)) - parseTimestamp(getTimestamp(a)));
}

function parseTimestamp(value: string | undefined | null) {
  const time = Date.parse(value ?? "");
  return Number.isFinite(time) ? time : 0;
}

function latestTimestamp<T>(items: T[], getTimestamp: (item: T) => string | undefined | null) {
  const latest = sortByTime(items, getTimestamp)[0];
  return latest ? getTimestamp(latest) : "";
}

function formatDateTime(value: string | undefined | null) {
  if (!value) return "not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatScore(value: number | undefined) {
  return typeof value === "number" ? value.toFixed(2) : "not scored";
}

function evalRunDetail(run: EvalRunSummary) {
  const outputCount =
    typeof run.output_count === "number" ? `${run.output_count} outputs` : "outputs not reported";
  const failureCount =
    typeof run.failure_count === "number" ? `${run.failure_count} failures` : "failures not reported";
  return `${outputCount} · ${failureCount}`;
}

function truncate(value: string, maxLength: number) {
  if (!value) return "";
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}
