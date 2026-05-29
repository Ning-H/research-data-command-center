import {
  ArrowLeft,
  ArrowRight,
  GitBranch,
  PackagePlus,
  Save,
} from "lucide-react";
import Link from "next/link";
import { revalidatePath } from "next/cache";
import { notFound, redirect } from "next/navigation";

import {
  createDatasetCandidateFromFailure,
  getFailure,
  listDatasets,
  updateFailureReview,
  type DatasetSummary,
  type EvalFailureDetail,
} from "../../../lib/api";

type FailureDetailPageProps = {
  params: {
    failureId: string;
  };
};

const ROOT_CAUSES = [
  ["", "Not assigned"],
  ["dataset_gap", "Dataset gap"],
  ["model_behavior", "Model behavior"],
  ["eval_rubric_issue", "Eval rubric issue"],
  ["prompt_issue", "Prompt issue"],
  ["acceptable_limitation", "Acceptable limitation"],
  ["logging_artifact", "Logging/artifact issue"],
];

export default async function FailureDetailPage({ params }: FailureDetailPageProps) {
  let failure: EvalFailureDetail;
  let datasets: DatasetSummary[] = [];
  try {
    [failure, datasets] = await Promise.all([getFailure(params.failureId), listDatasets()]);
  } catch {
    notFound();
  }

  return (
    <section className="page failure-detail-page">
      <nav className="breadcrumb">
        <Link href="/failure-library">
          <ArrowLeft aria-hidden="true" size={14} />
          Failure Library
        </Link>
        <span className="breadcrumb-sep">/</span>
        <span>eval_failure_id {failure.eval_failure_id}</span>
      </nav>

      <div className="dataset-overview">
        <div className="dataset-hero-panel">
          <div className="dataset-hero-topline">
            <div className="dataset-kicker">
              <span className={severityClass(failure.severity)}>{failure.severity}</span>
              <span>{failure.failure_type}</span>
              <span>eval_failure_id {failure.eval_failure_id}</span>
            </div>
            <div className="dataset-actions">
              <Link className="btn btn--secondary btn--sm" href="/failure-library">
                <ArrowLeft aria-hidden="true" size={15} />
                Queue
              </Link>
              <Link className="btn btn--secondary btn--sm" href="/dataset-iterations">
                Dataset iterations
                <ArrowRight aria-hidden="true" size={14} />
              </Link>
            </div>
          </div>

          <h1>{failure.case_name || `Failure ${failure.eval_failure_id}`}</h1>
          <p className="dataset-hero-desc">{failure.failure_reason}</p>

          <div className="dataset-fact-grid">
            <FailureFact label="Status" value={failure.status} valueClassName="meta-quality warn" />
            <FailureFact label="Score" value={formatScore(failure.score)} />
            <FailureFact label="Candidates" value={failure.dataset_candidate_count.toLocaleString()} />
            <FailureFact label="Root cause" value={failure.root_cause || "not assigned"} />
            <FailureFact label="Reviewed by" value={failure.reviewed_by_user_id || "not reviewed"} />
            <FailureFact label="Reviewed" value={formatDate(failure.reviewed_at)} />
          </div>
        </div>

        <aside className="dataset-schema-panel">
          <div className="dataset-schema-head">
            <span className="doc-label">Source Trace</span>
            <span>lineage</span>
          </div>
          <div className="failure-trace-stack">
            <TraceItem label="Dataset" value={`dataset ${failure.dataset_id} v${failure.dataset_version_id}`} />
            <TraceItem label="Run" value={`run ${failure.run_id}`} />
            <TraceItem label="Checkpoint" value={`checkpoint ${failure.checkpoint_id}`} />
            <TraceItem label="Model" value={failure.model_version_name ?? `model_version ${failure.model_version_id}`} />
            <TraceItem label="Eval run" value={`eval_run ${failure.eval_run_id}`} />
          </div>
        </aside>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Failure Evidence</h2>
            <p className="subtle">Compare the eval prompt, model output, rubric expectations, and captured evidence.</p>
          </div>
          <div className="description-box">
            <span>prompt</span>
            <p>{failure.prompt_text || "No prompt text stored."}</p>
          </div>
          <div className="description-box">
            <span>model output</span>
            <p>{failure.output_text || "No output text stored."}</p>
          </div>
          {failure.evidence_text ? (
            <div className="description-box">
              <span>evidence</span>
              <p>{failure.evidence_text}</p>
            </div>
          ) : null}
          <div className="score-grid">
            {Object.entries(failure.scores).map(([metric, value]) => (
              <div className="score-row" key={metric}>
                <span>{metric}</span>
                <strong>{formatScore(value)}</strong>
                <div className="score-track">
                  <span style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Validate Failure</h2>
            <p className="subtle">Record the researcher judgment before this failure becomes training data.</p>
          </div>
          <form action={updateFailureAction} className="form-grid">
            <input name="eval_failure_id" type="hidden" value={failure.eval_failure_id} />
            <label className="field">
              <span>status</span>
              <select name="status" defaultValue={failure.status}>
                <option value="open">open</option>
                <option value="in_review">in_review</option>
                <option value="valid_failure">valid_failure</option>
                <option value="candidate_created">candidate_created</option>
                <option value="resolved">resolved</option>
                <option value="dismissed">dismissed</option>
              </select>
            </label>
            <label className="field">
              <span>root_cause</span>
              <select name="root_cause" defaultValue={failure.root_cause || ""}>
                {ROOT_CAUSES.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <label className="field field-span-2">
              <span>review_notes</span>
              <textarea
                name="review_notes"
                defaultValue={failure.review_notes}
                placeholder="Why is this a valid failure, an eval issue, or safe to dismiss?"
              />
            </label>
            <label className="field">
              <span>reviewed_by_user_id</span>
              <input name="reviewed_by_user_id" defaultValue={failure.reviewed_by_user_id || "Lena Keys"} />
            </label>
            <div className="action-row field-span-2">
              <button className="btn btn--primary" type="submit">
                <Save aria-hidden="true" size={16} />
                Save review
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Create Dataset Candidate</h2>
            <p className="subtle">
              Pick an existing root dataset, then save the corrected example with this failure's lineage attached.
            </p>
          </div>
          <form action={createCandidate} className="form-grid">
            <input name="eval_failure_id" type="hidden" value={failure.eval_failure_id} />
            <label className="field field-span-2">
              <span>target dataset</span>
              <select name="target_dataset_id" defaultValue={failure.dataset_id || datasets[0]?.dataset_id} required>
                {datasets.map((dataset) => (
                  <option key={`${dataset.dataset_id}-${dataset.dataset_version_id}`} value={dataset.dataset_id}>
                    {dataset.name} · dataset {dataset.dataset_id} v{dataset.dataset_version_id}
                  </option>
                ))}
              </select>
            </label>
            <label className="field field-span-2">
              <span>proposed_input_text</span>
              <textarea name="proposed_input_text" defaultValue={defaultCandidateInput(failure)} required />
            </label>
            <label className="field field-span-2">
              <span>proposed_target_text</span>
              <textarea name="proposed_target_text" defaultValue={defaultCandidateTarget(failure)} required />
            </label>
            <label className="field field-span-2">
              <span>candidate_review_notes</span>
              <textarea
                name="review_notes"
                defaultValue="Created from validated eval failure. Review before publishing a new dataset version."
              />
            </label>
            <label className="field">
              <span>created_by_user_id</span>
              <input name="created_by_user_id" defaultValue="Lena Keys" />
            </label>
            <div className="action-row field-span-2">
              <button className="btn btn--primary" type="submit">
                <PackagePlus aria-hidden="true" size={16} />
                Save candidate
              </button>
            </div>
          </form>
        </div>

        <div className="panel">
          <div>
            <h2>Existing Candidates</h2>
            <p className="subtle">Candidate records already proposed from this failure.</p>
          </div>
          <div className="record-list">
            {failure.dataset_candidates.map((candidate) => (
              <article className="record" key={candidate.dataset_candidate_id}>
                <span className={candidateStatusClass(candidate.status, candidate.included_dataset_version_id)}>
                  {candidate.included_dataset_version_id ? "included" : candidate.status}
                </span>
                <strong>candidate_id {candidate.dataset_candidate_id}</strong>
                <p className="record-text">{candidate.proposed_target_text}</p>
                {candidate.review_notes ? <p className="muted-row">{candidate.review_notes}</p> : null}
                <div className="program-kicker">
                  <span>target dataset {candidate.target_dataset_id}</span>
                  <span>model_version {candidate.source_model_version_id}</span>
                  {candidate.included_dataset_version_id ? (
                    <span>included v{candidate.included_dataset_version_id}</span>
                  ) : null}
                </div>
                <Link
                  className="btn btn--secondary btn--sm"
                  href={`/dataset-iterations?target_dataset_id=${candidate.target_dataset_id}`}
                >
                  Review in iterations
                  <ArrowRight aria-hidden="true" size={14} />
                </Link>
              </article>
            ))}
            {!failure.dataset_candidates.length ? (
              <p className="subtle">No candidates have been created from this failure yet.</p>
            ) : null}
          </div>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Lineage</h2>
          <p className="subtle">This is the source chain a candidate will carry into dataset iteration review.</p>
        </div>
        <div className="failure-lineage-grid">
          {failure.lineage.map((edge) => (
            <article className="run-lineage-card" key={`${edge.lineage_step}-${edge.source_type}-${edge.target_type}`}>
              <div className="run-lineage-index">
                <GitBranch aria-hidden="true" size={15} />
              </div>
              <div className="run-lineage-body">
                <span className="run-lineage-label">{edge.lineage_step}</span>
                <div className="run-lineage-entities">
                  <span className="run-lineage-entity">
                    <span>{edge.source_type}</span>
                    <strong>{edge.source_id}</strong>
                  </span>
                  <span className="run-lineage-arrow">→</span>
                  <span className="run-lineage-entity">
                    <span>{edge.target_type}</span>
                    <strong>{edge.target_id}</strong>
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

async function updateFailureAction(formData: FormData) {
  "use server";
  const evalFailureId = String(formData.get("eval_failure_id") ?? "");
  if (!evalFailureId) {
    return;
  }
  await updateFailureReview(evalFailureId, {
    status: String(formData.get("status") ?? "open"),
    root_cause: String(formData.get("root_cause") ?? ""),
    review_notes: String(formData.get("review_notes") ?? ""),
    reviewed_by_user_id: String(formData.get("reviewed_by_user_id") ?? "Lena Keys"),
  });
  revalidatePath(`/failure-library/${evalFailureId}`);
  revalidatePath("/failure-library");
}

async function createCandidate(formData: FormData) {
  "use server";
  const evalFailureId = String(formData.get("eval_failure_id") ?? "");
  const targetDatasetId = Number(formData.get("target_dataset_id"));
  if (!evalFailureId || !Number.isInteger(targetDatasetId)) {
    return;
  }
  const createdBy = String(formData.get("created_by_user_id") ?? "Lena Keys");
  await createDatasetCandidateFromFailure(evalFailureId, {
    target_dataset_id: targetDatasetId,
    proposed_input_text: String(formData.get("proposed_input_text") ?? ""),
    proposed_target_text: String(formData.get("proposed_target_text") ?? ""),
    review_notes: String(formData.get("review_notes") ?? ""),
    created_by_user_id: createdBy,
  });
  await updateFailureReview(evalFailureId, {
    status: "candidate_created",
    reviewed_by_user_id: createdBy,
  });
  revalidatePath(`/failure-library/${evalFailureId}`);
  revalidatePath("/failure-library");
  revalidatePath("/dataset-iterations");
  redirect(`/dataset-iterations?target_dataset_id=${targetDatasetId}&status=proposed`);
}

function FailureFact({
  label,
  value,
  valueClassName = "",
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <div className="dataset-fact">
      <span>{label}</span>
      <strong className={valueClassName}>{value}</strong>
    </div>
  );
}

function TraceItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="lineage-meta-row">
      <span className="lineage-meta-label">{label}</span>
      <strong className="lineage-meta-value">{value}</strong>
    </div>
  );
}

function defaultCandidateInput(failure: EvalFailureDetail) {
  return failure.prompt_text || `Correct the failed case: ${failure.failure_reason}`;
}

function defaultCandidateTarget(failure: EvalFailureDetail) {
  const expected = failure.expected_topics.length
    ? `\n\nExpected topics: ${failure.expected_topics.join(", ")}.`
    : "";
  const sections = failure.required_sections.length
    ? `\nRequired sections: ${failure.required_sections.join(", ")}.`
    : "";
  return `Corrected response should address: ${failure.failure_reason}${expected}${sections}\n\nOriginal failed output:\n${failure.output_text}`;
}

function formatScore(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return value.toFixed(3);
}

function formatDate(value: string) {
  if (!value) {
    return "not reviewed";
  }
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

function severityClass(severity: string) {
  if (severity === "critical") {
    return "badge danger";
  }
  if (severity === "high") {
    return "badge warning";
  }
  return "badge neutral";
}

function candidateStatusClass(status: string, includedDatasetVersionId: number) {
  if (includedDatasetVersionId) {
    return "badge status-active";
  }
  if (status === "approved") {
    return "badge status-active";
  }
  if (status === "rejected") {
    return "badge warning";
  }
  return "badge neutral";
}
