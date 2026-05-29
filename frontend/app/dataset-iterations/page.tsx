import {
  ArrowRight,
  CheckCircle2,
  Clock3,
  Database,
  Filter,
  PackagePlus,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { revalidatePath } from "next/cache";

import {
  createDatasetVersionFromCandidates,
  listDatasetCandidates,
  listDatasetIterations,
  listDatasets,
  reviewDatasetCandidate,
  type DatasetCandidate,
  type DatasetIteration,
  type DatasetSummary,
} from "../../lib/api";

type DatasetIterationsPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

export default async function DatasetIterationsPage({ searchParams = {} }: DatasetIterationsPageProps) {
  const filters = normalizeFilters(searchParams);
  const [rawIterations, rawCandidates, datasets] = await Promise.all([
    listDatasetIterations(iterationApiFilters(filters)),
    listDatasetCandidates({ ...candidateApiFilters(filters), limit: 200 }),
    listDatasets(),
  ]);
  const candidates = filterByInclusion(rawCandidates, filters.inclusion_state);
  const iterations = filterIterationRows(rawIterations, filters);
  const datasetById = new Map(datasets.map((dataset) => [dataset.dataset_id, dataset]));
  const pending = candidates.filter((candidate) => candidate.status === "proposed");
  const approvedReady = candidates.filter(
    (candidate) => candidate.status === "approved" && !candidate.included_dataset_version_id,
  );
  const rejected = candidates.filter((candidate) => candidate.status === "rejected");
  const included = candidates.filter((candidate) => candidate.included_dataset_version_id > 0);
  const publishGroups = groupApprovedCandidates(approvedReady, datasetById);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Dataset Iterations</p>
          <h1>Failure-to-Data Review</h1>
          <p className="subtle">
            Review candidate records created from eval failures, approve the useful fixes, and publish
            immutable dataset versions for the next model iteration.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/failure-library">
          Failure library
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </div>

      <form className="filter-grid" action="/dataset-iterations">
        <Filter aria-hidden="true" className="accent-icon" size={18} />
        <label className="filter-field">
          <span>program</span>
          <input className="filter-input" defaultValue={filters.program_id ?? ""} name="program_id" placeholder="Any" />
        </label>
        <label className="filter-field">
          <span>experiment</span>
          <input className="filter-input" defaultValue={filters.experiment_id ?? ""} name="experiment_id" placeholder="Any" />
        </label>
        <label className="filter-field filter-field--wide">
          <span>target dataset</span>
          <select className="filter-input" defaultValue={filters.target_dataset_id ?? ""} name="target_dataset_id">
            <option value="">Any dataset</option>
            {datasets.map((dataset) => (
              <option key={`${dataset.dataset_id}-${dataset.dataset_version_id}`} value={dataset.dataset_id}>
                {dataset.name} · dataset {dataset.dataset_id}
              </option>
            ))}
          </select>
        </label>
        <label className="filter-field">
          <span>source model</span>
          <input
            className="filter-input"
            defaultValue={filters.source_model_version_id ?? ""}
            name="source_model_version_id"
            placeholder="Any"
          />
        </label>
        <label className="filter-field filter-field--wide">
          <span>failure type</span>
          <input className="filter-input" defaultValue={filters.failure_type ?? ""} name="failure_type" placeholder="Any type" />
        </label>
        <label className="filter-field">
          <span>status</span>
          <select className="filter-input" defaultValue={filters.status ?? ""} name="status">
            <option value="">Any</option>
            <option value="proposed">proposed</option>
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
          </select>
        </label>
        <label className="filter-field">
          <span>version state</span>
          <select className="filter-input" defaultValue={filters.inclusion_state ?? ""} name="inclusion_state">
            <option value="">Any</option>
            <option value="not_included">Not included</option>
            <option value="included">Included</option>
          </select>
        </label>
        <div className="filter-actions">
          <button className="btn btn--secondary btn--sm" type="submit">Apply</button>
          <Link className="btn btn--ghost btn--sm" href="/dataset-iterations">Clear</Link>
        </div>
      </form>

      <div className="summary-grid">
        <Metric label="Candidates" value={candidates.length.toLocaleString()} />
        <Metric label="Pending review" value={pending.length.toLocaleString()} />
        <Metric label="Approved to publish" value={approvedReady.length.toLocaleString()} />
        <Metric label="Included in versions" value={included.length.toLocaleString()} />
      </div>

      <div className="two-column">
        <div className="panel">
          <div>
            <h2>Publish Ready Groups</h2>
            <p className="subtle">
              Approved candidates are grouped by target dataset. Publishing creates a new immutable
              version and marks those candidates as included.
            </p>
          </div>
          <div className="record-list">
            {publishGroups.map((group) => (
              <article className="record" key={group.targetDatasetId}>
                <span className="badge status-active">{group.readyIds.length} approved</span>
                <strong>{group.datasetName}</strong>
                <p className="record-text">
                  dataset_id {group.targetDatasetId}. These records are ready to become a new dataset
                  version for later training or replay evaluation.
                </p>
                <form action={publishCandidates} className="candidate-review-form">
                  <input name="dataset_id" type="hidden" value={group.targetDatasetId} />
                  <input name="candidate_ids" type="hidden" value={group.readyIds.join(",")} />
                  <label className="field">
                    <span>version_notes</span>
                    <textarea
                      name="version_notes"
                      defaultValue={`Publish ${group.readyIds.length} approved failure-correction candidate(s).`}
                    />
                  </label>
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
            <p className="subtle">Grouped by dataset, review status, failure type, and source model version.</p>
          </div>
          <div className="record-list">
            {iterations.map((iteration) => (
              <article
                className="record"
                key={`${iteration.target_dataset_id}-${iteration.status}-${iteration.failure_type}-${iteration.source_model_version_id}`}
              >
                <span className={candidateStatusBadge(iteration.status, iteration.included_count)}>{iteration.status}</span>
                <strong>{datasetLabel(datasetById, iteration.target_dataset_id)}</strong>
                <p className="record-text">
                  {iteration.candidate_count} {iteration.failure_type} candidate(s) from model_version_id{" "}
                  {iteration.source_model_version_id}.
                  {iteration.included_count ? ` ${iteration.included_count} already included in dataset versions.` : ""}
                </p>
              </article>
            ))}
            {!iterations.length ? <p className="subtle">No iteration groups match the current filters.</p> : null}
          </div>
        </div>
      </div>

      <div className="panel panel-heading-row">
        <div>
          <h2>Candidate Review Board</h2>
          <p className="subtle">
            Approve, reject, or annotate each proposed correction before it can enter a new dataset version.
          </p>
        </div>
        <div className="status-stack">
          <span className="badge neutral"><Clock3 aria-hidden="true" size={12} /> {pending.length} pending</span>
          <span className="badge status-active"><CheckCircle2 aria-hidden="true" size={12} /> {approvedReady.length} ready</span>
          <span className="badge warning"><XCircle aria-hidden="true" size={12} /> {rejected.length} rejected</span>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Proposed Correction</th>
              <th>Source Lineage</th>
              <th>Version State</th>
              <th>Review Action</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate) => (
              <tr key={candidate.dataset_candidate_id}>
                <td>
                  <strong>candidate_id {candidate.dataset_candidate_id}</strong>
                  <div className="muted-row">
                    <Link href={`/failure-library/${candidate.eval_failure_id}`}>failure {candidate.eval_failure_id}</Link>
                  </div>
                  <div className="status-stack">
                    <span className={candidateStatusBadge(candidate.status, candidate.included_dataset_version_id)}>
                      {candidate.status}
                    </span>
                    <span className="badge neutral">{candidate.failure_type}</span>
                  </div>
                </td>
                <td>
                  <p className="table-copy">{candidate.proposed_input_text}</p>
                  <div className="description-box compact-box">
                    <span>target</span>
                    <p>{candidate.proposed_target_text}</p>
                  </div>
                  {candidate.review_notes ? <div className="muted-row">notes: {candidate.review_notes}</div> : null}
                </td>
                <td>
                  <strong>{datasetLabel(datasetById, candidate.target_dataset_id)}</strong>
                  <div className="muted-row">
                    <Database aria-hidden="true" size={12} /> target dataset {candidate.target_dataset_id}
                  </div>
                  <div className="muted-row">model_version_id {candidate.source_model_version_id}</div>
                  <div className="muted-row">eval_run_id {candidate.source_eval_run_id}</div>
                </td>
                <td>
                  {candidate.included_dataset_version_id ? (
                    <>
                      <span className="badge status-active">included</span>
                      <div className="muted-row">
                        dataset {candidate.included_dataset_id} v{candidate.included_dataset_version_id}
                      </div>
                      <div className="muted-row">{formatDate(candidate.included_at)}</div>
                    </>
                  ) : (
                    <>
                      <span className="badge neutral">not included</span>
                      <div className="muted-row">Publish after approval.</div>
                    </>
                  )}
                </td>
                <td>
                  <form action={reviewCandidate} className="candidate-review-form">
                    <input name="candidate_id" type="hidden" value={candidate.dataset_candidate_id} />
                    <input name="eval_failure_id" type="hidden" value={candidate.eval_failure_id} />
                    <label className="field">
                      <span>review_notes</span>
                      <textarea
                        name="review_notes"
                        defaultValue={candidate.review_notes || defaultReviewNote(candidate)}
                        disabled={candidate.included_dataset_version_id > 0}
                      />
                    </label>
                    <div className="action-row">
                      <button
                        className="btn btn--success btn--sm"
                        disabled={candidate.status === "approved" || candidate.included_dataset_version_id > 0}
                        name="status"
                        type="submit"
                        value="approved"
                      >
                        <CheckCircle2 aria-hidden="true" size={14} />
                        Approve
                      </button>
                      <button
                        className="btn btn--warning btn--sm"
                        disabled={candidate.status === "rejected" || candidate.included_dataset_version_id > 0}
                        name="status"
                        type="submit"
                        value="rejected"
                      >
                        <XCircle aria-hidden="true" size={14} />
                        Reject
                      </button>
                    </div>
                  </form>
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
  const evalFailureId = String(formData.get("eval_failure_id") ?? "");
  if (!candidateId || !status) {
    return;
  }
  await reviewDatasetCandidate(candidateId, {
    status,
    review_notes: reviewNotes,
    reviewed_by_user_id: "Lena Keys",
  });
  revalidatePath("/dataset-iterations");
  revalidatePath("/failure-library");
  if (evalFailureId) {
    revalidatePath(`/failure-library/${evalFailureId}`);
  }
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
  revalidatePath(`/datasets/${datasetId}`);
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
    program_id: single(searchParams.program_id),
    experiment_id: single(searchParams.experiment_id),
    target_dataset_id: single(searchParams.target_dataset_id),
    source_model_version_id: single(searchParams.source_model_version_id),
    failure_type: single(searchParams.failure_type),
    status: single(searchParams.status),
    inclusion_state: single(searchParams.inclusion_state),
  };
}

type DatasetIterationFilters = ReturnType<typeof normalizeFilters>;

function candidateApiFilters(filters: DatasetIterationFilters): Record<string, string | undefined> {
  return {
    program_id: filters.program_id,
    experiment_id: filters.experiment_id,
    target_dataset_id: filters.target_dataset_id,
    source_model_version_id: filters.source_model_version_id,
    failure_type: filters.failure_type,
    status: filters.status,
  };
}

function iterationApiFilters(filters: DatasetIterationFilters): Record<string, string | undefined> {
  return {
    program_id: filters.program_id,
    experiment_id: filters.experiment_id,
    target_dataset_id: filters.target_dataset_id,
    failure_type: filters.failure_type,
    status: filters.status,
  };
}

function single(value: string | string[] | undefined) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value || undefined;
}

function filterByInclusion(candidates: DatasetCandidate[], inclusionState?: string) {
  if (inclusionState === "included") {
    return candidates.filter((candidate) => candidate.included_dataset_version_id > 0);
  }
  if (inclusionState === "not_included") {
    return candidates.filter((candidate) => !candidate.included_dataset_version_id);
  }
  return candidates;
}

function filterIterationRows(iterations: DatasetIteration[], filters: DatasetIterationFilters) {
  if (!filters.source_model_version_id) {
    return iterations;
  }
  const modelVersionId = Number(filters.source_model_version_id);
  if (!Number.isInteger(modelVersionId)) {
    return iterations;
  }
  return iterations.filter((iteration) => iteration.source_model_version_id === modelVersionId);
}

function groupApprovedCandidates(
  candidates: DatasetCandidate[],
  datasetById: Map<number, DatasetSummary>,
) {
  const groups = new Map<number, DatasetCandidate[]>();
  for (const candidate of candidates) {
    const group = groups.get(candidate.target_dataset_id) ?? [];
    group.push(candidate);
    groups.set(candidate.target_dataset_id, group);
  }
  return [...groups.entries()].map(([targetDatasetId, group]) => {
    const dataset = datasetById.get(targetDatasetId);
    return {
      targetDatasetId,
      datasetName: dataset ? `${dataset.name} · dataset ${targetDatasetId}` : `dataset_id ${targetDatasetId}`,
      readyIds: group.map((candidate) => candidate.dataset_candidate_id),
    };
  });
}

function datasetLabel(datasetById: Map<number, DatasetSummary>, datasetId: number) {
  const dataset = datasetById.get(datasetId);
  return dataset ? `${dataset.name} · dataset ${datasetId}` : `dataset_id ${datasetId}`;
}

function candidateStatusBadge(status: string, includedCountOrVersion: number) {
  if (includedCountOrVersion > 0) {
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

function defaultReviewNote(candidate: DatasetCandidate) {
  if (candidate.status === "approved") {
    return "Approved for a failure-correction dataset version.";
  }
  if (candidate.status === "rejected") {
    return "Rejected during dataset-candidate review.";
  }
  return `Review whether this ${candidate.failure_type} correction should become training or eval data.`;
}

function formatDate(value: string) {
  if (!value) {
    return "";
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
