import { ArrowRight, CheckCircle2, PackagePlus, XCircle } from "lucide-react";
import Link from "next/link";
import { revalidatePath } from "next/cache";

import {
  createDatasetVersionFromCandidates,
  listDatasetCandidates,
  listDatasetIterations,
  reviewDatasetCandidate,
} from "../../lib/api";

type DatasetIterationsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function DatasetIterationsPage({ searchParams = {} }: DatasetIterationsPageProps) {
  const filters = normalizeFilters(searchParams);
  const [iterations, candidates] = await Promise.all([
    listDatasetIterations(filters),
    listDatasetCandidates(filters),
  ]);
  const approved = candidates.filter((candidate) => candidate.status === "approved");
  const included = candidates.filter((candidate) => candidate.included_dataset_version_id > 0);
  const pending = candidates.filter((candidate) => candidate.status === "proposed" || candidate.status === "pending_review");
  const publishGroups = groupApprovedCandidates(approved);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Dataset Iterations</p>
          <h1>Failure-to-Data Review</h1>
          <p className="subtle">
            Review examples produced from model failures, approve the useful ones, and publish the
            next immutable dataset version without mutating prior snapshots.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/failure-library">
          Failure library
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <form className="program-filters" action="/dataset-iterations">
        <input className="filter-input" defaultValue={filters.experiment_id ?? ""} name="experiment_id" placeholder="experiment_id" />
        <input className="filter-input" defaultValue={filters.target_dataset_id ?? ""} name="target_dataset_id" placeholder="target_dataset_id" />
        <input className="filter-input" defaultValue={filters.failure_type ?? ""} name="failure_type" placeholder="failure_type" />
        <select className="filter-input" defaultValue={filters.status ?? ""} name="status">
          <option value="">Any status</option>
          <option value="proposed">proposed</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
        </select>
        <button className="btn btn--secondary btn--sm" type="submit">Apply</button>
        <Link className="btn btn--ghost btn--sm" href="/dataset-iterations">Clear</Link>
      </form>

      <div className="summary-grid">
        <Metric label="Candidates" value={candidates.length.toLocaleString()} />
        <Metric label="Pending review" value={pending.length.toLocaleString()} />
        <Metric label="Approved" value={approved.length.toLocaleString()} />
        <Metric label="Included in versions" value={included.length.toLocaleString()} />
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Publish Ready Groups</h2>
            <p className="subtle">
              Approved candidates are grouped by target dataset. Publishing creates a new immutable
              version from selected candidate records.
            </p>
          </div>
          <div className="record-list">
            {publishGroups.map((group) => (
              <article className="record" key={group.targetDatasetId}>
                <span className="badge">{group.candidates.length} approved</span>
                <strong>dataset_id {group.targetDatasetId}</strong>
                <p className="record-text">
                  {group.includedCount} already included. {group.readyCount} candidate records are ready
                  for a new version.
                </p>
                <form action={publishCandidates} className="action-row">
                  <input name="dataset_id" type="hidden" value={group.targetDatasetId} />
                  <input name="candidate_ids" type="hidden" value={group.readyIds.join(",")} />
                  <input name="version_notes" type="hidden" value="Publish approved evaluation-failure corrections." />
                  <button className="btn btn--primary btn--sm" disabled={!group.readyIds.length} type="submit">
                    <PackagePlus aria-hidden="true" size={14} />
                    Publish version
                  </button>
                </form>
              </article>
            ))}
            {!publishGroups.length ? <p className="subtle">No approved candidates are ready to publish yet.</p> : null}
          </div>
        </div>

        <div className="panel">
          <div>
            <h2>Iteration Summary</h2>
            <p className="subtle">Grouped by dataset, status, failure type, and source model version.</p>
          </div>
          <div className="record-list">
            {iterations.map((iteration) => (
              <article className="record" key={`${iteration.target_dataset_id}-${iteration.status}-${iteration.failure_type}-${iteration.source_model_version_id}`}>
                <span className={iteration.status === "approved" ? "badge" : "badge neutral"}>{iteration.status}</span>
                <strong>dataset_id {iteration.target_dataset_id}</strong>
                <p className="record-text">
                  {iteration.candidate_count} {iteration.failure_type} candidates from model_version_id {iteration.source_model_version_id}.
                  {iteration.included_count ? ` ${iteration.included_count} already included in dataset versions.` : ""}
                </p>
              </article>
            ))}
            {!iterations.length ? <p className="subtle">No iteration groups match the current filters.</p> : null}
          </div>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Proposed Record</th>
              <th>Source</th>
              <th>Status</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate) => (
              <tr key={candidate.dataset_candidate_id}>
                <td>
                  <strong>candidate_id {candidate.dataset_candidate_id}</strong>
                  <div className="muted-row">failure {candidate.eval_failure_id}</div>
                  <div className="muted-row">target dataset_id {candidate.target_dataset_id}</div>
                </td>
                <td>
                  <p className="table-copy">{candidate.proposed_input_text}</p>
                  <div className="muted-row">{candidate.proposed_target_text}</div>
                </td>
                <td>
                  model_version_id {candidate.source_model_version_id}
                  <div className="muted-row">eval_run_id {candidate.source_eval_run_id}</div>
                  <div className="muted-row">{candidate.failure_type}</div>
                </td>
                <td>
                  <span className={candidateStatusClass(candidate)}>{candidate.status}</span>
                  {candidate.included_dataset_version_id ? (
                    <div className="muted-row">
                      included in dataset_version_id {candidate.included_dataset_version_id}
                    </div>
                  ) : null}
                </td>
                <td>
                  <div className="action-row">
                    <form action={reviewCandidate}>
                      <input name="candidate_id" type="hidden" value={candidate.dataset_candidate_id} />
                      <input name="status" type="hidden" value="approved" />
                      <input name="review_notes" type="hidden" value="Approved for the next failure-correction dataset version." />
                      <button className="btn btn--success btn--sm" disabled={candidate.status === "approved"} type="submit">
                        <CheckCircle2 aria-hidden="true" size={14} />
                        Approve
                      </button>
                    </form>
                    <form action={reviewCandidate}>
                      <input name="candidate_id" type="hidden" value={candidate.dataset_candidate_id} />
                      <input name="status" type="hidden" value="rejected" />
                      <input name="review_notes" type="hidden" value="Rejected during dataset-candidate review." />
                      <button className="btn btn--warning btn--sm" disabled={candidate.status === "rejected"} type="submit">
                        <XCircle aria-hidden="true" size={14} />
                        Reject
                      </button>
                    </form>
                  </div>
                </td>
              </tr>
            ))}
            {!candidates.length ? (
              <tr>
                <td colSpan={5}>
                  <p className="subtle">No dataset candidates match the current filters.</p>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}

async function reviewCandidate(formData: FormData) {
  "use server";
  const candidateId = String(formData.get("candidate_id") ?? "");
  const status = String(formData.get("status") ?? "");
  const reviewNotes = String(formData.get("review_notes") ?? "");
  if (!candidateId || !status) {
    return;
  }
  await reviewDatasetCandidate(candidateId, {
    status,
    review_notes: reviewNotes,
    reviewed_by_user_id: "Lena Keys",
  });
  revalidatePath("/dataset-iterations");
}

async function publishCandidates(formData: FormData) {
  "use server";
  const datasetId = String(formData.get("dataset_id") ?? "");
  const candidateIds = String(formData.get("candidate_ids") ?? "")
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value > 0);
  if (!datasetId || !candidateIds.length) {
    return;
  }
  await createDatasetVersionFromCandidates(datasetId, {
    candidate_ids: candidateIds,
    version_notes: String(formData.get("version_notes") ?? ""),
    created_by_user_id: "Lena Keys",
  });
  revalidatePath("/dataset-iterations");
  revalidatePath("/datasets");
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <p className="metric-label">{label}</p>
      <p className="metric-value">{value}</p>
    </div>
  );
}

function normalizeFilters(searchParams: Record<string, string | string[] | undefined>) {
  return {
    experiment_id: single(searchParams.experiment_id),
    target_dataset_id: single(searchParams.target_dataset_id),
    failure_type: single(searchParams.failure_type),
    status: single(searchParams.status),
  };
}

function single(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value || undefined;
}

function groupApprovedCandidates(candidates: Awaited<ReturnType<typeof listDatasetCandidates>>) {
  const groups = new Map<number, Awaited<ReturnType<typeof listDatasetCandidates>>>();
  for (const candidate of candidates) {
    const group = groups.get(candidate.target_dataset_id) ?? [];
    group.push(candidate);
    groups.set(candidate.target_dataset_id, group);
  }
  return [...groups.entries()].map(([targetDatasetId, group]) => {
    const readyIds = group
      .filter((candidate) => !candidate.included_dataset_version_id)
      .map((candidate) => candidate.dataset_candidate_id);
    return {
      targetDatasetId,
      candidates: group,
      includedCount: group.length - readyIds.length,
      readyCount: readyIds.length,
      readyIds,
    };
  });
}

function candidateStatusClass(candidate: { status: string; included_dataset_version_id: number }) {
  if (candidate.included_dataset_version_id) {
    return "badge";
  }
  if (candidate.status === "approved") {
    return "badge status-active";
  }
  if (candidate.status === "rejected") {
    return "badge warning";
  }
  return "badge neutral";
}
