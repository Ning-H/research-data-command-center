import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  ClipboardCheck,
  Filter,
  GitBranch,
  ShieldCheck,
  Trophy,
} from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import type { EvalRunSummary, ModelVersionSummary } from "../../lib/api";
import { getEvaluationSummary, listModels } from "../../lib/api";

type ModelsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

type ModelFilters = {
  program_id?: string;
  experiment_id?: string;
  status?: string;
  model?: string;
  readiness?: string;
};

type ModelEvalStats = {
  evalRunCount: number;
  outputCount: number;
  failureCount: number;
  latestEvalRunId?: number;
  bestMetricName?: string;
  bestScore?: number;
};

type FamilySummary = {
  modelId: number;
  modelName: string;
  versionCount: number;
  promotedCount: number;
  evaluatedCount: number;
  bestModel?: ModelVersionSummary;
  bestScore?: number;
  bestMetricName?: string;
};

export default async function ModelsPage({ searchParams = {} }: ModelsPageProps) {
  const filters = normalizeFilters(searchParams);
  const [allModels, evaluationSummary] = await Promise.all([
    listModels(),
    getEvaluationSummary({
      program_id: filters.program_id,
      experiment_id: filters.experiment_id,
    }),
  ]);
  const modelEvalStats = buildEvalStats(evaluationSummary.runs);
  const models = applyFilters(allModels, filters, modelEvalStats);
  const programOptions = uniqueLinkedOptions(allModels.map((model) => model.program_id));
  const experimentOptions = uniqueLinkedOptions(
    allModels
      .filter((model) => !filters.program_id || String(model.program_id || "") === filters.program_id)
      .map((model) => model.experiment_id),
  );
  const uniqueModels = new Set(models.map((model) => model.model_id)).size;
  const candidateCount = models.filter((model) => model.status === "candidate").length;
  const promotedCount = models.filter((model) => model.status === "promoted").length;
  const reviewReadyCount = models.filter(hasReviewContext).length;
  const evalPlanCount = models.filter(hasEvalPlan).length;
  const evaluatedCount = models.filter((model) => hasEvaluation(model, modelEvalStats)).length;
  const attentionItems = buildAttentionItems(models, modelEvalStats);
  const bestEvaluatedModel = bestEvaluated(models, modelEvalStats);
  const familySummaries = buildFamilySummaries(models, modelEvalStats);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Models</p>
          <h1>Models</h1>
          <p className="subtle">
            Review model versions created from promoted checkpoints, then decide what needs context,
            evaluation, comparison, or promotion.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/runs/checkpoints">
          Review checkpoints
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <form className="model-filter-form" action="/models">
        <label className="run-filter-field">
          <span>program_id</span>
          <select defaultValue={filters.program_id ?? ""} name="program_id">
            <option value="">all programs</option>
            {programOptions.map((programId) => (
              <option key={programId} value={programId}>program {programId}</option>
            ))}
          </select>
        </label>
        <label className="run-filter-field">
          <span>experiment_id</span>
          <select defaultValue={filters.experiment_id ?? ""} name="experiment_id">
            <option value="">all experiments</option>
            {experimentOptions.map((experimentId) => (
              <option key={experimentId} value={experimentId}>experiment {experimentId}</option>
            ))}
          </select>
        </label>
        <label className="run-filter-field">
          <span>status</span>
          <select defaultValue={filters.status ?? ""} name="status">
            <option value="">all statuses</option>
            <option value="candidate">candidate</option>
            <option value="registered">registered</option>
            <option value="promoted">promoted</option>
            <option value="archived">archived</option>
          </select>
        </label>
        <label className="run-filter-field">
          <span>model</span>
          <input defaultValue={filters.model ?? ""} name="model" placeholder="name or id" />
        </label>
        <label className="run-filter-field">
          <span>readiness</span>
          <select defaultValue={filters.readiness ?? ""} name="readiness">
            <option value="">all readiness</option>
            <option value="needs_context">needs context</option>
            <option value="needs_eval_plan">needs eval plan</option>
            <option value="unevaluated">unevaluated</option>
            <option value="has_failures">has failures</option>
            <option value="decision_pending">decision pending</option>
          </select>
        </label>
        <div className="run-filter-actions">
          <button className="btn btn--secondary btn--sm" type="submit">
            <Filter aria-hidden="true" size={14} />
            Apply
          </button>
          <Link className="btn btn--ghost btn--sm" href="/models">Clear</Link>
        </div>
      </form>

      <div className="summary-grid">
        <Metric label="Model families" value={uniqueModels.toLocaleString()} />
        <Metric label="Model versions" value={models.length.toLocaleString()} />
        <Metric label="Candidates" value={candidateCount.toLocaleString()} />
        <Metric label="Promoted" value={promotedCount.toLocaleString()} />
      </div>

      <div className="panel">
        <div>
          <h2>Readiness Funnel</h2>
          <p className="subtle">
            How many model versions have the evidence needed for a real research decision.
          </p>
        </div>
        <div className="component-grid">
          <AnalysisCard icon={<Boxes aria-hidden="true" size={18} />} label="created" value={models.length.toLocaleString()}>
            Model versions created from checkpoint promotion.
          </AnalysisCard>
          <AnalysisCard icon={<ShieldCheck aria-hidden="true" size={18} />} label="review context" value={`${reviewReadyCount}/${models.length || 0}`}>
            Intended use and promotion reason are present.
          </AnalysisCard>
          <AnalysisCard icon={<ClipboardCheck aria-hidden="true" size={18} />} label="eval plan" value={`${evalPlanCount}/${models.length || 0}`}>
            Expected eval suites are attached.
          </AnalysisCard>
          <AnalysisCard icon={<Trophy aria-hidden="true" size={18} />} label="evaluated" value={`${evaluatedCount}/${models.length || 0}`}>
            At least one eval run exists for the model version.
          </AnalysisCard>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Needs Attention</h2>
            <p className="subtle">
              The fastest path to make model versions useful for comparison and review.
            </p>
          </div>
          <div className="record-list">
            {attentionItems.map((item) => (
              <article className="record" key={item.label}>
                <span className={item.count ? "badge warning" : "badge"}>{item.count}</span>
                <strong>{item.label}</strong>
                <p className="record-text">{item.detail}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Best Evaluated Model</h2>
            <p className="subtle">
              Driven by eval scores when they exist. Training metrics stay in the table as source context.
            </p>
          </div>
          {bestEvaluatedModel ? (
            <div className="record">
              <span className="badge">best {bestEvaluatedModel.stats.bestMetricName}</span>
              <strong>{bestEvaluatedModel.model.model_version_name}</strong>
              <p className="record-text">
                {formatMetric(bestEvaluatedModel.stats.bestScore)} mean score · {bestEvaluatedModel.stats.evalRunCount} eval runs · {bestEvaluatedModel.stats.failureCount} failures.
              </p>
              <div className="program-kicker">
                <span>program {displayLinkedId(bestEvaluatedModel.model.program_id)}</span>
                <span>experiment {displayLinkedId(bestEvaluatedModel.model.experiment_id)}</span>
                <span>model_version_id {bestEvaluatedModel.model.model_version_id}</span>
              </div>
              <Link className="btn btn--secondary btn--sm" href={`/models/${bestEvaluatedModel.model.model_version_id}`}>
                Open model
                <ArrowRight aria-hidden="true" size={14} />
              </Link>
            </div>
          ) : (
            <EmptyState text="No evaluated model versions match the current filters." />
          )}
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Model Family Comparison</h2>
          <p className="subtle">
            Each family groups versions that share a `model_id`; use this to see where variants are accumulating.
          </p>
        </div>
        <div className="component-grid">
          {familySummaries.map((family) => (
            <FamilyCard family={family} key={family.modelId} />
          ))}
          {!familySummaries.length ? <EmptyState text="No model families match the current filters." /> : null}
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Model Version Boundary</h2>
          <p className="subtle">
            Review metadata can change after promotion; source lineage and artifact identity stay locked.
          </p>
        </div>
        <div className="component-grid">
          <WorkflowCard icon={<ShieldCheck aria-hidden="true" size={18} />} title="Editable review context">
            Status, intended use, notes, owners, tags, and expected eval suites can change.
          </WorkflowCard>
          <WorkflowCard icon={<GitBranch aria-hidden="true" size={18} />} title="Locked source lineage">
            Checkpoint, run, dataset version, artifact URI, and metrics snapshot stay fixed.
          </WorkflowCard>
          <WorkflowCard icon={<AlertTriangle aria-hidden="true" size={18} />} title="New version required">
            Different weights, checkpoint, base model, data, or behavior-affecting config.
          </WorkflowCard>
          <WorkflowCard icon={<ClipboardCheck aria-hidden="true" size={18} />} title="Evaluation evidence">
            Scores, failures, and comparisons attach to the same model version.
          </WorkflowCard>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Model Version</th>
              <th>Program / Experiment</th>
              <th>Source</th>
              <th>Eval Signal</th>
              <th>Readiness</th>
              <th>Status</th>
              <th>Intended Use</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {models.map((model) => {
              const stats = modelEvalStats.get(model.model_version_id);
              const readiness = readinessState(model, modelEvalStats);
              return (
                <tr key={model.model_version_id}>
                  <td>
                    <strong>{model.model_version_name}</strong>
                    <div className="muted-row">{model.model_name}</div>
                    <div className="muted-row mono">model_version_id {model.model_version_id}</div>
                    <div className="muted-row mono">model_id {model.model_id}</div>
                  </td>
                  <td>
                    program {displayLinkedId(model.program_id)}
                    <div className="muted-row">experiment {displayLinkedId(model.experiment_id)}</div>
                    <div className="muted-row">{model.source_experiment_name}</div>
                  </td>
                  <td>
                    checkpoint_id {model.checkpoint_id}
                    <div className="muted-row">run_id {model.run_id} · step {model.source_checkpoint_step}</div>
                    <div className="muted-row">dataset {model.dataset_id} v{model.dataset_version_id}</div>
                  </td>
                  <td>
                    {stats?.bestMetricName ? (
                      <>
                        {stats.bestMetricName} {formatMetric(stats.bestScore)}
                        <div className="muted-row">{stats.evalRunCount} eval runs · {stats.failureCount} failures</div>
                      </>
                    ) : (
                      <>
                        no evals yet
                        <div className="muted-row">train.acc {formatMetric(model.metrics_snapshot["train.accuracy"])}</div>
                      </>
                    )}
                  </td>
                  <td>
                    <span className={readiness.tone === "warn" ? "badge warning" : "badge neutral"}>
                      {readiness.label}
                    </span>
                    <div className="muted-row">{readiness.detail}</div>
                  </td>
                  <td>
                    <span className={model.status === "promoted" ? "badge" : "badge neutral"}>
                      {model.status}
                    </span>
                  </td>
                  <td>{model.intended_use || "not provided"}</td>
                  <td>
                    <Link className="btn btn--secondary btn--sm" href={`/models/${model.model_version_id}`}>
                      Detail
                      <ArrowRight aria-hidden="true" size={14} />
                    </Link>
                  </td>
                </tr>
              );
            })}
            {!models.length ? (
              <tr>
                <td colSpan={8}>
                  <EmptyState text="No model versions match the current filters." />
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

function AnalysisCard({
  children,
  icon,
  label,
  value,
}: {
  children: string;
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="component-card">
      <span>{icon}</span>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{children}</p>
    </div>
  );
}

function FamilyCard({ family }: { family: FamilySummary }) {
  return (
    <div className="component-card">
      <span>model_id {family.modelId}</span>
      <strong>{family.modelName}</strong>
      <p>
        {family.versionCount} versions · {family.evaluatedCount} evaluated · {family.promotedCount} promoted
      </p>
      <p>
        Best: {family.bestModel ? `${family.bestModel.model_version_name} (${family.bestMetricName} ${formatMetric(family.bestScore)})` : "not evaluated"}
      </p>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="subtle">{text}</p>;
}

function normalizeFilters(searchParams: Record<string, string | string[] | undefined>): ModelFilters {
  return {
    program_id: single(searchParams.program_id),
    experiment_id: single(searchParams.experiment_id),
    status: single(searchParams.status),
    model: single(searchParams.model),
    readiness: single(searchParams.readiness),
  };
}

function single(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value || undefined;
}

function applyFilters(
  models: ModelVersionSummary[],
  filters: ModelFilters,
  evalStats: Map<number, ModelEvalStats>,
) {
  return models.filter((model) => {
    if (filters.program_id && String(model.program_id || "") !== filters.program_id) {
      return false;
    }
    if (filters.experiment_id && String(model.experiment_id || "") !== filters.experiment_id) {
      return false;
    }
    if (filters.status && model.status !== filters.status) {
      return false;
    }
    if (filters.model) {
      const needle = filters.model.toLowerCase();
      const haystack = `${model.model_id} ${model.model_name} ${model.model_version_name}`.toLowerCase();
      if (!haystack.includes(needle)) {
        return false;
      }
    }
    if (filters.readiness && readinessFilter(model, evalStats) !== filters.readiness) {
      return false;
    }
    return true;
  });
}

function uniqueLinkedOptions(values: Array<number | null | undefined>) {
  return Array.from(new Set(values.filter((value): value is number => Boolean(value))))
    .sort((left, right) => left - right);
}

function readinessFilter(model: ModelVersionSummary, evalStats: Map<number, ModelEvalStats>) {
  if (!hasReviewContext(model)) {
    return "needs_context";
  }
  if (!hasEvalPlan(model)) {
    return "needs_eval_plan";
  }
  if (!hasEvaluation(model, evalStats)) {
    return "unevaluated";
  }
  if ((evalStats.get(model.model_version_id)?.failureCount ?? 0) > 0) {
    return "has_failures";
  }
  if (model.status === "candidate") {
    return "decision_pending";
  }
  return "ready";
}

function readinessState(model: ModelVersionSummary, evalStats: Map<number, ModelEvalStats>) {
  const state = readinessFilter(model, evalStats);
  switch (state) {
    case "needs_context":
      return { label: "needs context", detail: "Add intended use and promotion reason.", tone: "warn" };
    case "needs_eval_plan":
      return { label: "needs eval plan", detail: "Attach expected eval suites.", tone: "warn" };
    case "unevaluated":
      return { label: "unevaluated", detail: "No eval runs attached yet.", tone: "warn" };
    case "has_failures":
      return { label: "review failures", detail: "Eval failures need inspection.", tone: "warn" };
    case "decision_pending":
      return { label: "decision pending", detail: "Evaluated candidate needs a decision.", tone: "neutral" };
    default:
      return { label: "ready", detail: "Evidence is attached.", tone: "neutral" };
  }
}

function hasReviewContext(model: ModelVersionSummary) {
  return Boolean((model.intended_use ?? "").trim() && (model.promotion_reason ?? "").trim());
}

function hasEvalPlan(model: ModelVersionSummary) {
  return model.expected_eval_suite_ids.length > 0;
}

function hasEvaluation(model: ModelVersionSummary, evalStats: Map<number, ModelEvalStats>) {
  return (evalStats.get(model.model_version_id)?.evalRunCount ?? 0) > 0;
}

function buildEvalStats(runs: EvalRunSummary[]) {
  const stats = new Map<number, ModelEvalStats>();
  for (const run of runs) {
    const modelStats = stats.get(run.model_version_id) ?? {
      evalRunCount: 0,
      outputCount: 0,
      failureCount: 0,
    };
    modelStats.evalRunCount += 1;
    modelStats.outputCount += run.output_count;
    modelStats.failureCount += run.failure_count;
    modelStats.latestEvalRunId ??= run.eval_run_id;
    for (const [metricName, score] of Object.entries(run.score_summary)) {
      const mean = score.mean;
      if (modelStats.bestScore === undefined || mean > modelStats.bestScore) {
        modelStats.bestScore = mean;
        modelStats.bestMetricName = metricName;
      }
    }
    stats.set(run.model_version_id, modelStats);
  }
  return stats;
}

function buildAttentionItems(models: ModelVersionSummary[], evalStats: Map<number, ModelEvalStats>) {
  const missingContext = models.filter((model) => !hasReviewContext(model)).length;
  const missingEvalPlan = models.filter((model) => !hasEvalPlan(model)).length;
  const unevaluated = models.filter((model) => !hasEvaluation(model, evalStats)).length;
  const hasFailures = models.filter((model) => (evalStats.get(model.model_version_id)?.failureCount ?? 0) > 0).length;
  const decisionPending = models.filter(
    (model) => model.status === "candidate" && hasEvaluation(model, evalStats) && hasReviewContext(model),
  ).length;
  return [
    {
      label: "Missing review context",
      count: missingContext,
      detail: "Add intended use and promotion reason so other researchers know why this version exists.",
    },
    {
      label: "Missing eval plan",
      count: missingEvalPlan,
      detail: "Attach expected eval suites before treating the model as reviewable.",
    },
    {
      label: "No eval runs yet",
      count: unevaluated,
      detail: "Run evaluations before comparing or promoting a candidate.",
    },
    {
      label: "Failures to inspect",
      count: hasFailures,
      detail: "Review failure cases before deciding whether the model should advance.",
    },
    {
      label: "Decision pending",
      count: decisionPending,
      detail: "Evaluated candidates still marked as candidate need a promote, archive, or continue decision.",
    },
  ];
}

function bestEvaluated(models: ModelVersionSummary[], evalStats: Map<number, ModelEvalStats>) {
  return models.reduce<{ model: ModelVersionSummary; stats: ModelEvalStats } | undefined>((best, model) => {
    const stats = evalStats.get(model.model_version_id);
    if (!stats || stats.bestScore === undefined) {
      return best;
    }
    if (!best || stats.bestScore > (best.stats.bestScore ?? Number.NEGATIVE_INFINITY)) {
      return { model, stats };
    }
    return best;
  }, undefined);
}

function buildFamilySummaries(models: ModelVersionSummary[], evalStats: Map<number, ModelEvalStats>) {
  const byFamily = new Map<number, ModelVersionSummary[]>();
  for (const model of models) {
    byFamily.set(model.model_id, [...(byFamily.get(model.model_id) ?? []), model]);
  }
  return Array.from(byFamily.entries())
    .map(([modelId, familyModels]) => {
      const best = bestEvaluated(familyModels, evalStats);
      return {
        modelId,
        modelName: familyModels[0].model_name,
        versionCount: familyModels.length,
        promotedCount: familyModels.filter((model) => model.status === "promoted").length,
        evaluatedCount: familyModels.filter((model) => hasEvaluation(model, evalStats)).length,
        bestModel: best?.model,
        bestScore: best?.stats.bestScore,
        bestMetricName: best?.stats.bestMetricName,
      };
    })
    .sort((left, right) => right.versionCount - left.versionCount || left.modelName.localeCompare(right.modelName));
}

function displayLinkedId(value: number | null | undefined) {
  return value ? value : "unlinked";
}

function formatMetric(value: number | undefined) {
  if (value === undefined) {
    return "not logged";
  }
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
}
