import { ArrowRight, FlaskConical, Plus } from "lucide-react";
import Link from "next/link";

import { listExperiments, listResearchPrograms } from "../../lib/api";

export const dynamic = "force-dynamic";

type ExperimentsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function ExperimentsPage({ searchParams = {} }: ExperimentsPageProps) {
  const q = first(searchParams.q) ?? "";
  const status = first(searchParams.status) ?? "";
  const programId = first(searchParams.program_id) ?? "";

  const [experiments, allExperiments, programs] = await Promise.all([
    listExperiments({ q, status, program_id: programId }),
    listExperiments({}),
    listResearchPrograms({}),
  ]);
  const programNames = new Map(programs.map((program) => [program.program_id, program.program_name]));
  const activeCount = allExperiments.filter((experiment) => experiment.status === "active").length;
  const datasetLinks = allExperiments.reduce(
    (sum, experiment) => sum + experiment.linked_datasets.length,
    0,
  );
  const runLinks = allExperiments.reduce((sum, experiment) => sum + experiment.linked_run_ids.length, 0);
  const modelLinks = allExperiments.reduce(
    (sum, experiment) => sum + experiment.linked_model_version_ids.length,
    0,
  );

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Experiments</p>
          <h1>Experiment Registry</h1>
          <p className="subtle">
            Hypothesis-driven research tests connected to dataset versions, runs, models, and evals.
          </p>
        </div>
        <Link className="btn btn--primary" href="/experiments/new">
          <Plus aria-hidden="true" size={16} />
          Register experiment
        </Link>
      </div>

      <div className="summary-grid">
        <div className="metric">
          <p className="metric-label">Experiments</p>
          <p className="metric-value">{allExperiments.length}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Active</p>
          <p className="metric-value">{activeCount}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Dataset links</p>
          <p className="metric-value">{datasetLinks}</p>
        </div>
        <div className="metric">
          <p className="metric-label">Runs / Models</p>
          <p className="metric-value">{runLinks} / {modelLinks}</p>
        </div>
      </div>

      <form className="program-filters" action="/experiments">
        <input
          className="filter-input"
          defaultValue={q}
          name="q"
          placeholder="Search by name, question, hypothesis, type, tags..."
        />
        <select className="filter-input" defaultValue={programId} name="program_id">
          <option value="">Any program</option>
          {programs.map((program) => (
            <option key={program.program_id} value={program.program_id}>
              {program.program_name}
            </option>
          ))}
        </select>
        <select className="filter-input" defaultValue={status} name="status">
          <option value="">Any status</option>
          <option value="planning">Planning</option>
          <option value="active">Active</option>
          <option value="paused">Paused</option>
          <option value="completed">Completed</option>
          <option value="archived">Archived</option>
        </select>
        <button className="btn btn--secondary" type="submit">
          Filter
        </button>
      </form>

      <div className="table-wrap experiment-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Experiment</th>
              <th>Program</th>
              <th>Status / Type</th>
              <th>Linked records</th>
              <th>Owner / Updated</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {experiments.map((experiment) => (
              <tr className="program-row" key={experiment.experiment_id}>
                <td>
                  <Link className="program-name-link" href={`/experiments/${experiment.experiment_id}`}>
                    <FlaskConical aria-hidden="true" className="accent-icon" size={15} />
                    {experiment.experiment_name}
                  </Link>
                  <div className="muted-row">
                    {truncate(experiment.research_question || experiment.hypothesis, 120)}
                  </div>
                </td>
                <td>{programNames.get(experiment.program_id) ?? `Program ${experiment.program_id}`}</td>
                <td>
                  <span className={statusBadgeClass(experiment.status)}>{experiment.status}</span>
                  <div className="tag-row">
                    <span className="badge neutral">{humanize(experiment.experiment_type)}</span>
                  </div>
                </td>
                <td>
                  <div className="muted-row">{experiment.linked_datasets.length} datasets</div>
                  <div className="muted-row">
                    {experiment.linked_run_ids.length} runs · {experiment.linked_model_version_ids.length} models
                  </div>
                </td>
                <td>
                  {experiment.owner_name || "Unassigned"}
                  <div className="muted-row">{formatDate(experiment.updated_at)}</div>
                </td>
                <td>
                  <Link className="btn btn--secondary btn--sm" href={`/experiments/${experiment.experiment_id}`}>
                    Detail
                    <ArrowRight aria-hidden="true" size={15} />
                  </Link>
                </td>
              </tr>
            ))}
            {!experiments.length && (
              <tr>
                <td colSpan={6}>
                  <p className="subtle">No experiments match the current filters.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function statusBadgeClass(status: string) {
  const map: Record<string, string> = {
    active: "badge status-active",
    planning: "badge status-planning",
    paused: "badge status-paused",
    completed: "badge status-completed",
    archived: "badge status-archived",
  };
  return map[status] ?? "badge neutral";
}

function humanize(value: string) {
  return value ? value.replaceAll("_", " ") : "unspecified";
}

function truncate(value: string, maxLength: number) {
  if (!value) return "No research question recorded.";
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
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

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}
