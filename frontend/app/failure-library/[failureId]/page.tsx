import { ArrowLeft, ArrowRight, Database, GitBranch, PackagePlus } from "lucide-react";
import Link from "next/link";
import { revalidatePath } from "next/cache";
import { notFound, redirect } from "next/navigation";
import type { ReactNode } from "react";

import { createDatasetCandidateFromFailure, getFailure } from "../../../lib/api";

type FailureDetailPageProps = {
  params: {
    failureId: string;
  };
};

export default async function FailureDetailPage({ params }: FailureDetailPageProps) {
  const failure = await getFailure(params.failureId).catch(() => null);
  if (!failure) {
    notFound();
  }

  return (
    <section className="page">
      <div className="breadcrumb">
        <Link href="/failure-library">
          <ArrowLeft aria-hidden="true" size={14} />
          Failure Library
        </Link>
        <span className="breadcrumb-sep">/</span>
        <span>eval_failure_id {failure.eval_failure_id}</span>
      </div>

      <div className="page-header">
        <div>
          <p className="eyebrow">Failure Review</p>
          <h1>{failure.case_name || `Failure ${failure.eval_failure_id}`}</h1>
          <p className="subtle">
            Inspect the failed output, keep the lineage visible, and save a corrected example as a
            candidate for the next dataset version.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/dataset-iterations">
          Dataset iterations
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <div className="summary-grid">
        <Metric label="Failure type" value={failure.failure_type} compact />
        <Metric label="Severity" value={failure.severity} compact />
        <Metric label="Score" value={formatScore(failure.score)} />
        <Metric label="Candidates" value={failure.dataset_candidate_count.toLocaleString()} />
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Failed Output</h2>
            <p className="subtle">{failure.failure_reason}</p>
          </div>
          <div className="description-box">
            <span>prompt</span>
            <p>{failure.prompt_text || "No prompt text stored."}</p>
          </div>
          <div className="description-box">
            <span>model output</span>
            <p>{failure.output_text || "No output text stored."}</p>
          </div>
          {Object.keys(failure.scores).length ? (
            <div className="metadata-grid">
              {Object.entries(failure.scores).map(([metric, value]) => (
                <Metadata key={metric} label={metric} value={formatScore(value)} />
              ))}
            </div>
          ) : null}
        </div>

        <div className="panel">
          <div>
            <h2>Create Dataset Candidate</h2>
            <p className="subtle">
              This stores a proposed corrected record linked back to the eval failure, model version,
              run, checkpoint, and source dataset.
            </p>
          </div>
          <form action={createCandidate} className="form-grid">
            <input name="eval_failure_id" type="hidden" value={failure.eval_failure_id} />
            <label className="field">
              <span>target_dataset_id</span>
              <input name="target_dataset_id" required type="number" defaultValue={failure.dataset_id || 1} />
            </label>
            <label className="field">
              <span>created_by_user_id</span>
              <input name="created_by_user_id" defaultValue="Lena Keys" />
            </label>
            <label className="field field-span-2">
              <span>proposed_input_text</span>
              <textarea name="proposed_input_text" defaultValue={defaultCandidateInput(failure)} required />
            </label>
            <label className="field field-span-2">
              <span>proposed_target_text</span>
              <textarea name="proposed_target_text" defaultValue={defaultCandidateTarget(failure)} required />
            </label>
            <div className="action-row field-span-2">
              <button className="btn btn--primary" type="submit">
                <PackagePlus aria-hidden="true" size={16} />
                Save candidate
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Lineage</h2>
            <p className="subtle">The candidate inherits this context instead of relying on notes.</p>
          </div>
          <div className="record-list">
            {failure.lineage.map((edge) => (
              <article className="record" key={`${edge.lineage_step}-${edge.source_type}-${edge.target_type}`}>
                <span className="badge neutral">{edge.lineage_step}</span>
                <strong>{edge.source_type} {edge.source_id}</strong>
                <p className="record-text">to {edge.target_type} {edge.target_id}</p>
              </article>
            ))}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Existing Candidates</h2>
            <p className="subtle">Previously created records from this failure.</p>
          </div>
          <div className="record-list">
            {failure.dataset_candidates.map((candidate) => (
              <article className="record" key={candidate.dataset_candidate_id}>
                <span className={candidate.status === "approved" ? "badge" : "badge neutral"}>{candidate.status}</span>
                <strong>candidate_id {candidate.dataset_candidate_id}</strong>
                <p className="record-text">{candidate.proposed_target_text}</p>
                <div className="program-kicker">
                  <span>target dataset_id {candidate.target_dataset_id}</span>
                  <span>source model_version_id {candidate.source_model_version_id}</span>
                </div>
              </article>
            ))}
            {!failure.dataset_candidates.length ? <p className="subtle">No candidates have been created from this failure yet.</p> : null}
          </div>
        </div>
      </div>

      <div className="panel">
        <div>
          <h2>Source Context</h2>
          <p className="subtle">Use these IDs to trace the failed behavior back through the research lifecycle.</p>
        </div>
        <div className="component-grid">
          <ContextCard icon={<Database aria-hidden="true" size={18} />} title="Dataset">
            dataset_id {failure.dataset_id}, dataset_version_id {failure.dataset_version_id}
          </ContextCard>
          <ContextCard icon={<GitBranch aria-hidden="true" size={18} />} title="Run + checkpoint">
            run_id {failure.run_id}, checkpoint_id {failure.checkpoint_id}
          </ContextCard>
          <ContextCard icon={<PackagePlus aria-hidden="true" size={18} />} title="Model + eval">
            model_version_id {failure.model_version_id}, eval_run_id {failure.eval_run_id}
          </ContextCard>
        </div>
      </div>
    </section>
  );
}

async function createCandidate(formData: FormData) {
  "use server";
  const evalFailureId = String(formData.get("eval_failure_id") ?? "");
  const targetDatasetId = Number(formData.get("target_dataset_id"));
  if (!evalFailureId || !Number.isInteger(targetDatasetId)) {
    return;
  }
  await createDatasetCandidateFromFailure(evalFailureId, {
    target_dataset_id: targetDatasetId,
    proposed_input_text: String(formData.get("proposed_input_text") ?? ""),
    proposed_target_text: String(formData.get("proposed_target_text") ?? ""),
    created_by_user_id: String(formData.get("created_by_user_id") ?? "Lena Keys"),
  });
  revalidatePath(`/failure-library/${evalFailureId}`);
  revalidatePath("/failure-library");
  revalidatePath("/dataset-iterations");
  redirect("/dataset-iterations");
}

function Metric({
  compact = false,
  label,
  value,
}: {
  compact?: boolean;
  label: string;
  value: string;
}) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className={compact ? "metric-value compact" : "metric-value"}>{value}</p>
    </div>
  );
}

function Metadata({ label, value }: { label: string; value: string }) {
  return (
    <div className="metadata-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ContextCard({
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

function defaultCandidateInput(failure: { prompt_text: string; failure_reason: string }) {
  return failure.prompt_text || `Correct the failed case: ${failure.failure_reason}`;
}

function defaultCandidateTarget(failure: { output_text: string; failure_reason: string }) {
  return `Corrected response should address: ${failure.failure_reason}\n\nOriginal failed output:\n${failure.output_text}`;
}

function formatScore(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return value.toFixed(3);
}
