import Link from "next/link";
import { redirect } from "next/navigation";

import {
  createExperiment,
  listDatasets,
  listResearchPrograms,
  type DatasetRef,
  type ExperimentVariant,
} from "../../../lib/api";

export const dynamic = "force-dynamic";

const EXPERIMENT_TYPES = [
  ["baseline_comparison", "Baseline comparison"],
  ["dataset_ablation", "Dataset ablation"],
  ["prompt_strategy_comparison", "Prompt strategy comparison"],
  ["model_checkpoint_comparison", "Model checkpoint comparison"],
  ["failure_replay_comparison", "Failure replay comparison"],
  ["rubric_regression_check", "Rubric regression check"],
  ["data_mixture_comparison", "Data mixture comparison"],
  ["training_config_comparison", "Training config comparison"],
  ["human_review_study", "Human review study"],
  ["other", "Other"],
];

const VARIANT_TYPES = [
  ["control", "Control"],
  ["test", "Test"],
  ["ablation", "Ablation"],
  ["candidate", "Candidate"],
];

export default async function NewExperimentPage() {
  const [programs, datasets] = await Promise.all([listResearchPrograms({}), listDatasets()]);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Experiments</p>
          <h1>Register Experiment</h1>
          <p className="subtle">
            Create the research test record before attaching runs, evals, and failure-derived data.
          </p>
        </div>
        <Link className="btn btn--secondary" href="/experiments">
          All experiments
        </Link>
      </div>

      <form className="panel form-panel experiment-form-panel" action={registerExperiment}>
        <div>
          <h2>Experiment Overview</h2>
          <p className="subtle">Choose the parent program, experiment type, owner, and status.</p>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>research_program</span>
            <select name="program_id" required>
              <option value="">Select a program</option>
              {programs.map((program) => (
                <option key={program.program_id} value={program.program_id}>
                  {program.program_name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>experiment_name</span>
            <input
              name="experiment_name"
              required
              placeholder="Failure-correction replay for shallow guides"
            />
          </label>
          <label className="field">
            <span>experiment_type</span>
            <select name="experiment_type" defaultValue="failure_replay_comparison">
              {EXPERIMENT_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>status</span>
            <select name="status" defaultValue="planning">
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label className="field">
            <span>owner_name</span>
            <input name="owner_name" placeholder="Lena Keys" />
          </label>
          <label className="field">
            <span>tags</span>
            <input name="tags" placeholder="failure_replay, study_material, rubric_eval" />
          </label>
        </div>

        <label className="field">
          <span>experiment_description</span>
          <textarea
            name="experiment_description"
            placeholder="What this experiment tests and why it matters."
          />
        </label>
        <label className="field">
          <span>primary_research_question</span>
          <textarea
            name="research_question"
            placeholder="Do failure-derived corrected examples improve explanation depth?"
          />
        </label>
        <label className="field">
          <span>primary_hypothesis</span>
          <textarea
            name="hypothesis"
            placeholder="Adding corrected shallow-output examples should improve depth, examples, and learning flow."
          />
        </label>
        <label className="field">
          <span>evaluation_plan</span>
          <textarea
            name="evaluation_plan"
            placeholder="Metrics, rubric, eval suite, baseline, and promotion rule."
          />
        </label>
        <label className="field">
          <span>decision_notes</span>
          <textarea
            name="decision_notes"
            placeholder="Stable decision context for this experiment."
          />
        </label>

        <label className="field">
          <span>linked_datasets</span>
          <select name="linked_datasets" multiple size={Math.min(8, Math.max(3, datasets.length))}>
            {datasets.map((dataset) => (
              <option
                key={`${dataset.dataset_id}:${dataset.dataset_version_id}`}
                value={`${dataset.dataset_id}:${dataset.dataset_version_id}`}
              >
                {dataset.name} · dataset {dataset.dataset_id} · v{dataset.dataset_version_id}
              </option>
            ))}
          </select>
        </label>

        <div className="doc-section">
          <span className="doc-label">Variants</span>
          <div className="variant-form-grid">
            {[0, 1, 2].map((index) => (
              <div className="description-box" key={index}>
                <div className="form-grid">
                  <label className="field">
                    <span>variant_name</span>
                    <input name={`variant_${index}_name`} placeholder={index === 0 ? "control" : "failure_replay"} />
                  </label>
                  <label className="field">
                    <span>variant_type</span>
                    <select name={`variant_${index}_type`} defaultValue={index === 0 ? "control" : "test"}>
                      {VARIANT_TYPES.map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <label className="field">
                  <span>description</span>
                  <textarea name={`variant_${index}_description`} placeholder="What changes in this arm?" />
                </label>
                <label className="field">
                  <span>variant_linked_datasets</span>
                  <select name={`variant_${index}_datasets`} multiple size={Math.min(5, Math.max(3, datasets.length))}>
                    {datasets.map((dataset) => (
                      <option
                        key={`${index}-${dataset.dataset_id}:${dataset.dataset_version_id}`}
                        value={`${dataset.dataset_id}:${dataset.dataset_version_id}`}
                      >
                        {dataset.name} · dataset {dataset.dataset_id} · v{dataset.dataset_version_id}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ))}
          </div>
        </div>

        <div className="action-row">
          <Link className="btn btn--secondary" href="/experiments">
            Cancel
          </Link>
          <button className="btn btn--primary" type="submit">
            Register experiment
          </button>
        </div>
      </form>
    </section>
  );
}

async function registerExperiment(formData: FormData) {
  "use server";

  const experiment = await createExperiment({
    decision_notes: field(formData, "decision_notes"),
    evaluation_plan: field(formData, "evaluation_plan"),
    experiment_description: field(formData, "experiment_description"),
    experiment_name: field(formData, "experiment_name"),
    experiment_type: field(formData, "experiment_type") || "other",
    hypothesis: field(formData, "hypothesis"),
    linked_datasets: datasetRefs(formData.getAll("linked_datasets")),
    owner_name: field(formData, "owner_name"),
    program_id: Number(field(formData, "program_id")),
    research_question: field(formData, "research_question"),
    status: field(formData, "status") || "planning",
    tags: commaList(formData, "tags"),
    variants: variantRows(formData),
  });
  redirect(`/experiments/${experiment.experiment_id}`);
}

function variantRows(formData: FormData): ExperimentVariant[] {
  return [0, 1, 2].flatMap((index) => {
    const variantName = field(formData, `variant_${index}_name`);
    const description = field(formData, `variant_${index}_description`);
    const linkedDatasets = datasetRefs(formData.getAll(`variant_${index}_datasets`));
    if (!variantName && !description && linkedDatasets.length === 0) {
      return [];
    }
    return [
      {
        description,
        linked_datasets: linkedDatasets,
        variant_name: variantName || `variant_${index + 1}`,
        variant_type: field(formData, `variant_${index}_type`) || "test",
      },
    ];
  });
}

function datasetRefs(values: FormDataEntryValue[]): DatasetRef[] {
  return values.flatMap((value) => {
    const [datasetId, datasetVersionId] = String(value).split(":").map(Number);
    if (!datasetId || !datasetVersionId) {
      return [];
    }
    return [{ dataset_id: datasetId, dataset_version_id: datasetVersionId }];
  });
}

function field(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

function commaList(formData: FormData, name: string) {
  return field(formData, name)
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
}
