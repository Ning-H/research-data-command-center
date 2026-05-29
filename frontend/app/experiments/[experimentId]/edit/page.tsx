import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import {
  getExperiment,
  listDatasets,
  updateExperiment,
  type DatasetRef,
  type ExperimentVariant,
} from "../../../../lib/api";

export const dynamic = "force-dynamic";

type EditExperimentPageProps = {
  params: {
    experimentId: string;
  };
};

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
  ["study_material_structure_comparison", "Study material structure comparison"],
  ["other", "Other"],
];

const VARIANT_TYPES = [
  ["control", "Control"],
  ["test", "Test"],
  ["ablation", "Ablation"],
  ["candidate", "Candidate"],
];

export default async function EditExperimentPage({ params }: EditExperimentPageProps) {
  const [datasets, experimentResult] = await Promise.all([
    listDatasets(),
    getExperiment(params.experimentId).catch(() => null),
  ]);
  if (!experimentResult) {
    notFound();
  }
  const experiment = experimentResult;
  const variantCount = Math.max(3, experiment.variants.length);
  const linkedDatasetValues = experiment.linked_datasets.map(datasetValue);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Experiments</p>
          <h1>Edit Experiment</h1>
          <p className="subtle">{experiment.experiment_name}</p>
        </div>
        <Link className="btn btn--secondary" href={`/experiments/${experiment.experiment_id}`}>
          Experiment detail
        </Link>
      </div>

      <form className="panel form-panel experiment-form-panel" action={saveExperiment}>
        <input name="experiment_id" type="hidden" value={experiment.experiment_id} />
        <div>
          <h2>Experiment Overview</h2>
          <p className="subtle">Update the hypothesis, status, dataset links, and variants.</p>
        </div>

        <div className="form-grid">
          <label className="field">
            <span>experiment_name</span>
            <input name="experiment_name" required defaultValue={experiment.experiment_name} />
          </label>
          <label className="field">
            <span>experiment_type</span>
            <select name="experiment_type" defaultValue={experiment.experiment_type || "other"}>
              {EXPERIMENT_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>status</span>
            <select name="status" defaultValue={experiment.status}>
              <option value="planning">Planning</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </label>
          <label className="field">
            <span>owner_name</span>
            <input name="owner_name" defaultValue={experiment.owner_name} />
          </label>
          <label className="field field-span-2">
            <span>tags</span>
            <input name="tags" defaultValue={experiment.tags.join(", ")} />
          </label>
        </div>

        <label className="field">
          <span>experiment_description</span>
          <textarea name="experiment_description" defaultValue={experiment.experiment_description} />
        </label>
        <label className="field">
          <span>primary_research_question</span>
          <textarea name="research_question" defaultValue={experiment.research_question} />
        </label>
        <label className="field">
          <span>primary_hypothesis</span>
          <textarea name="hypothesis" defaultValue={experiment.hypothesis} />
        </label>
        <label className="field">
          <span>evaluation_plan</span>
          <textarea name="evaluation_plan" defaultValue={experiment.evaluation_plan} />
        </label>
        <label className="field">
          <span>decision_context</span>
          <textarea name="decision_notes" defaultValue={experiment.decision_notes} />
        </label>

        <label className="field">
          <span>linked_datasets</span>
          <select
            defaultValue={linkedDatasetValues}
            multiple
            name="linked_datasets"
            size={Math.min(8, Math.max(3, datasets.length))}
          >
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
            {Array.from({ length: variantCount }).map((_, index) => {
              const variant = experiment.variants[index];
              return (
                <div className="description-box" key={index}>
                  <input
                    name={`variant_${index}_id`}
                    type="hidden"
                    value={variant?.variant_id ?? index + 1}
                  />
                  <div className="form-grid">
                    <label className="field">
                      <span>variant_name</span>
                      <input name={`variant_${index}_name`} defaultValue={variant?.variant_name ?? ""} />
                    </label>
                    <label className="field">
                      <span>variant_type</span>
                      <select name={`variant_${index}_type`} defaultValue={variant?.variant_type ?? "test"}>
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
                    <textarea
                      name={`variant_${index}_description`}
                      defaultValue={variant?.description ?? ""}
                    />
                  </label>
                  <label className="field">
                    <span>variant_linked_datasets</span>
                    <select
                      defaultValue={(variant?.linked_datasets ?? []).map(datasetValue)}
                      multiple
                      name={`variant_${index}_datasets`}
                      size={Math.min(5, Math.max(3, datasets.length))}
                    >
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
              );
            })}
          </div>
        </div>

        <div className="action-row">
          <Link className="btn btn--secondary" href={`/experiments/${experiment.experiment_id}`}>
            Cancel
          </Link>
          <button className="btn btn--primary" type="submit">
            Save updates
          </button>
        </div>
      </form>
    </section>
  );
}

async function saveExperiment(formData: FormData) {
  "use server";

  const experimentId = field(formData, "experiment_id");
  await updateExperiment(experimentId, {
    decision_notes: field(formData, "decision_notes"),
    evaluation_plan: field(formData, "evaluation_plan"),
    experiment_description: field(formData, "experiment_description"),
    experiment_name: field(formData, "experiment_name"),
    experiment_type: field(formData, "experiment_type") || "other",
    hypothesis: field(formData, "hypothesis"),
    linked_datasets: datasetRefs(formData.getAll("linked_datasets")),
    owner_name: field(formData, "owner_name"),
    research_question: field(formData, "research_question"),
    status: field(formData, "status") || "planning",
    tags: commaList(formData, "tags"),
    variants: variantRows(formData),
  });
  redirect(`/experiments/${experimentId}`);
}

function variantRows(formData: FormData): ExperimentVariant[] {
  const rows: ExperimentVariant[] = [];
  for (let index = 0; index < 12; index += 1) {
    if (!formData.has(`variant_${index}_name`)) {
      continue;
    }
    const variantName = field(formData, `variant_${index}_name`);
    const description = field(formData, `variant_${index}_description`);
    const linkedDatasets = datasetRefs(formData.getAll(`variant_${index}_datasets`));
    if (!variantName && !description && linkedDatasets.length === 0) {
      continue;
    }
    rows.push({
      description,
      linked_datasets: linkedDatasets,
      variant_id: Number(field(formData, `variant_${index}_id`)) || index + 1,
      variant_name: variantName || `variant_${index + 1}`,
      variant_type: field(formData, `variant_${index}_type`) || "test",
    });
  }
  return rows;
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

function datasetValue(dataset: DatasetRef) {
  return `${dataset.dataset_id}:${dataset.dataset_version_id}`;
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
