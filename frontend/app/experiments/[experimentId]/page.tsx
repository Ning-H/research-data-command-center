import { ArrowLeft, PlayCircle } from "lucide-react";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import {
  appendExperimentNote,
  getExperiment,
  getExperimentEvaluationSummary,
  getExperimentNextRunPlan,
  getResearchProgram,
  type DatasetRef,
  type ExperimentDetail,
  type ExperimentNextRunPlan,
  type EvaluationSummary,
} from "../../../lib/api";
import ExperimentEditableFields from "./ExperimentEditableFields";

export const dynamic = "force-dynamic";

type ExperimentDetailPageProps = {
  params: {
    experimentId: string;
  };
};

export default async function ExperimentDetailPage({ params }: ExperimentDetailPageProps) {
  let experiment: ExperimentDetail;
  let nextRunPlan: ExperimentNextRunPlan | null = null;
  let evaluationSummary: EvaluationSummary | null = null;
  let programName = "";

  try {
    experiment = await getExperiment(params.experimentId);
  } catch {
    notFound();
  }

  try {
    const program = await getResearchProgram(String(experiment.program_id));
    programName = program.program_name;
  } catch {
    programName = `Program ${experiment.program_id}`;
  }

  try {
    nextRunPlan = await getExperimentNextRunPlan(params.experimentId);
  } catch {
    nextRunPlan = null;
  }

  try {
    evaluationSummary = await getExperimentEvaluationSummary(params.experimentId);
  } catch {
    evaluationSummary = null;
  }

  return (
    <section className="page program-detail-page experiment-detail-page">
      <nav className="breadcrumb">
        <Link href="/experiments">Experiments</Link>
        <span className="breadcrumb-sep" aria-hidden="true">/</span>
        <span>{experiment.experiment_name}</span>
      </nav>

      <div className="dataset-actions experiment-top-actions">
        <Link className="btn btn--secondary btn--sm" href="/experiments">
          <ArrowLeft aria-hidden="true" size={15} />
          Registry
        </Link>
      </div>

      <div className="program-doc">
        <div className="doc-main">
          <ExperimentEditableFields initialExperiment={experiment} programName={programName} />

          <div className="doc-section">
            <div className="doc-section-heading">
              <span className="doc-label highlight">Variants</span>
              <span className="muted-row">
                {experiment.variants.length || 0} planned comparison arms
              </span>
            </div>
            {experiment.variants.length ? (
              <div className="variant-card-grid">
                {experiment.variants.map((variant, index) => (
                  <article className="variant-card" key={`${variant.variant_name}-${index}`}>
                    <div className="variant-card-head">
                      <h2>{variant.variant_name}</h2>
                      <span className="badge neutral">{variant.variant_type}</span>
                    </div>
                    <p className={variant.description ? "doc-text" : "doc-text empty"}>
                      {variant.description || "No variant description recorded."}
                    </p>
                    <DatasetLinkChips linkedDatasets={variant.linked_datasets ?? []} compact />
                  </article>
                ))}
              </div>
            ) : (
              <p className="doc-text empty">No variants recorded.</p>
            )}
          </div>

          <div className="doc-section">
            <div className="doc-section-heading">
              <span className="doc-label">Linked Datasets</span>
              <span className="muted-row">Planned, used, or handoff-linked dataset versions</span>
            </div>
            <DatasetLinkChips linkedDatasets={experiment.linked_datasets} />
          </div>

          {nextRunPlan && (
            <div className="doc-section">
              <span className="doc-label">Next Run Plan</span>
              <div className="description-box">
                <div className="doc-lineage-header">
                  <PlayCircle aria-hidden="true" className="accent-icon" size={17} />
                  <strong>{String(nextRunPlan.run_registration_payload.run_name ?? "Next run")}</strong>
                </div>
                <p>
                  {nextRunPlan.evaluation_requirement.summary}
                </p>
                <div className="tag-row">
                  {nextRunPlan.next_actions.slice(0, 4).map((action) => (
                    <span className="badge neutral" key={action}>{action}</span>
                  ))}
                  {evaluationSummary ? (
                    <span className="badge neutral">
                      {evaluationSummary.eval_run_count} eval runs · {evaluationSummary.failure_count} failures
                    </span>
                  ) : null}
                </div>
              </div>
            </div>
          )}

          <div className="doc-section">
            <span className="doc-label">Decision Notes</span>
            {experiment.notes.length > 0 ? (
              <div className="chat-thread">
                {experiment.notes.map((note) => (
                  <div className="chat-message" key={note.note_id}>
                    <div className="chat-avatar" aria-hidden="true">
                      {(note.author_name || "?")[0].toUpperCase()}
                    </div>
                    <div className="chat-bubble">
                      <div className="chat-meta">
                        <span className="chat-author">{note.author_name || "Anonymous"}</span>
                        <span className="chat-time">{note.created_at}</span>
                      </div>
                      <p className="chat-body">{note.body}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="doc-text empty">No decision notes yet.</p>
            )}
          </div>

          <div className="doc-section">
            <form action={appendDecisionNote} className="chat-compose">
              <input name="experiment_id" type="hidden" value={experiment.experiment_id} />
              <div className="chat-avatar" aria-hidden="true">
                {(experiment.owner_name || "?")[0].toUpperCase()}
              </div>
              <div className="chat-compose-body">
                <textarea
                  className="chat-compose-input"
                  name="body"
                  placeholder="Add a decision note..."
                  required
                />
                <div className="chat-compose-footer">
                  <input
                    className="chat-compose-author"
                    defaultValue={experiment.owner_name || ""}
                    name="author_name"
                    placeholder="Your name"
                  />
                  <button className="btn btn--primary" type="submit">
                    Post note
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}

function DatasetLinkChips({
  linkedDatasets,
  compact = false,
}: {
  linkedDatasets: DatasetRef[];
  compact?: boolean;
}) {
  if (!linkedDatasets.length) {
    return <p className="doc-text empty">No dataset versions linked yet.</p>;
  }
  return (
    <div className={compact ? "dataset-chip-row dataset-chip-row--compact" : "dataset-chip-row"}>
      {linkedDatasets.map((dataset, index) => (
        <Link
          className="dataset-link-chip"
          href={`/datasets/${dataset.dataset_id}`}
          key={`${dataset.dataset_id}-${dataset.dataset_version_id}-${index}`}
        >
          <span>dataset {dataset.dataset_id}</span>
          <strong>v{dataset.dataset_version_id}</strong>
          {!compact && (
            <em>
              {dataset.link_origin ?? "legacy"}
              {dataset.link_role ? ` · ${dataset.link_role}` : ""}
              {dataset.source?.type ? ` · ${String(dataset.source.type)}` : ""}
            </em>
          )}
        </Link>
      ))}
    </div>
  );
}

async function appendDecisionNote(formData: FormData) {
  "use server";

  const experimentId = String(formData.get("experiment_id") ?? "").trim();
  await appendExperimentNote(experimentId, {
    author_name: String(formData.get("author_name") ?? "").trim() || undefined,
    body: String(formData.get("body") ?? "").trim(),
  });
  redirect(`/experiments/${experimentId}`);
}
