const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DatasetSummary = {
  dataset_id: number;
  dataset_version_id: number;
  name: string;
  source_dataset_name: string;
  source_url: string;
  task_type: string;
  data_purpose: string;
  data_format: string;
  query_engine: string;
  description: string;
  category: string;
  source_label: string;
  record_count: number;
  quality_status: string;
  quality_score: number;
  quality_label: string;
  registration_date: string;
  last_updated_date: string;
  created_at: string;
};

export type QualityMetric = {
  metric_name: string;
  metric_value: number;
  source_priority: string;
  timestamp: string;
};

export type SchemaField = {
  field_name: string;
  field_type: string;
  non_null_count: number;
  null_count: number;
  empty_count: number;
  distinct_count: number;
  min_length: number;
  max_length: number;
  mean_length: number;
};

export type DatasetRecord = {
  record_id: number;
  source_split: string;
  source_row_id: string;
  category: string;
  task_type: string;
  input_text: string;
  instruction: string;
  context: string;
  question: string;
  chosen_text: string;
  rejected_text: string;
  target_text: string;
  response_text: string;
  content_hash: string;
};

export type DatasetLineage = {
  dataset_id: number;
  source_dataset_version_id: number | string;
  target_dataset_version_id: number;
  source_label: string;
  lineage_event_type: string;
  transform_name: string;
  transform_config_uri: string;
  created_at: string;
  created_by_user_id: string;
};

export type QualityCheck = {
  name: string;
  status: string;
  metric_name: string;
  metric_value: number;
  description: string;
};

export type QualitySummary = {
  status: string;
  score: number;
  score_label: string;
  score_explanation: string;
  framework: string;
  meaning: string;
  procedure: string[];
  score_components: {
    name: string;
    weight: number;
    description: string;
  }[];
  required_fields: string[];
  null_value_policy: string;
  total_null_values: number;
  fields_with_nulls: number;
  checks: QualityCheck[];
};

export type DatasetDetail = DatasetSummary & {
  quality_summary: QualitySummary;
  quality_metrics: QualityMetric[];
  schema_profile: SchemaField[];
  lineage: DatasetLineage[];
  sample_records: DatasetRecord[];
};

export type RunHealthSummary = {
  health_score: number;
  health_label: string;
  signals: string[];
};

export type RunSummary = {
  run_id: number;
  run_name: string;
  experiment_name: string;
  dataset_id: number;
  dataset_version_id: number;
  run_config_id: number;
  model_family: string;
  status: string;
  ingest_source: string;
  training_environment: string;
  raw_events_uri: string;
  source_priority: string;
  started_at: string;
  ended_at: string;
  created_by_user_id: string;
  checkpoint_count: number;
  model_version_status: string;
  health_summary: RunHealthSummary;
};

export type RunMetric = {
  run_id?: number;
  timestamp: string;
  step: number;
  metric_name?: string;
  metric_value: number;
};

export type RunCheckpoint = {
  checkpoint_id: number;
  run_id: number;
  dataset_version_id: number;
  step: number;
  status: string;
  artifact_uri: string;
  checkpoint_uri: string;
  metrics_snapshot: Record<string, number>;
  created_at: string;
};

export type CheckpointSearchResult = RunCheckpoint & {
  rank: number;
  is_best_for_filter: boolean;
  run_name: string;
  experiment_name: string;
  dataset_id: number;
  run_config_id: number;
  model_family: string;
  framework: string;
  trainer: string;
  device: string;
  run_status: string;
  source_priority: string;
  training_environment: string;
  ingest_source: string;
  ranking_metric: string;
  ranking_value: number | null;
  promotion_status: string;
};

export type ModelLineageEdge = {
  lineage_step: string;
  source_type: string;
  source_id: number;
  target_type: string;
  target_id: number;
};

export type ModelVersionSummary = {
  model_id: number;
  model_version_id: number;
  model_name: string;
  model_version_name: string;
  checkpoint_id: number;
  run_id: number;
  dataset_id: number;
  dataset_version_id: number;
  run_config_id: number;
  source_run_name: string;
  source_experiment_name: string;
  base_model_name: string;
  source_checkpoint_step: number;
  status: string;
  artifact_uri: string;
  registry_manifest_uri: string;
  intended_use: string;
  promotion_reason: string;
  promotion_notes: string;
  expected_eval_suite_ids: string[];
  metrics_snapshot: Record<string, number>;
  source_priority: string;
  created_at: string;
  created_by_user_id: string;
  lineage_summary: {
    dataset_id: number;
    dataset_version_id: number;
    run_id: number;
    checkpoint_id: number;
    model_version_id: number;
  };
};

export type ModelVersionDetail = ModelVersionSummary & {
  lineage: ModelLineageEdge[];
};

export type RegisterModelPayload = {
  checkpoint_id: number;
  model_name: string;
  model_version_name: string;
  intended_use: string;
  promotion_reason: string;
  promotion_notes: string;
  owner_user_id: string;
};

export type RegisterModelResponse = {
  model_id: number;
  model_version_id: number;
  checkpoint_id: number;
  run_id: number;
  dataset_id: number;
  dataset_version_id: number;
  status: string;
  artifact_uri: string;
};

export type EvalMetricSummary = {
  metric_name: string;
  mean: number;
  min: number;
  max: number;
  best_eval_run_id: number;
  best_model_version_id: number;
};

export type EvalRunSummary = {
  eval_run_id: number;
  eval_suite_id: number;
  program_id: number;
  experiment_id: number;
  model_version_id: number;
  dataset_id: number;
  dataset_version_id: number;
  checkpoint_id: number;
  run_id: number;
  status: string;
  started_at: string;
  ended_at: string;
  source_priority: string;
  model_name?: string;
  model_version_name?: string;
  output_count: number;
  failure_count: number;
  failure_types: Record<string, number>;
  score_summary: Record<string, { mean: number; min: number; max: number }>;
  lineage_summary: {
    dataset_id: number;
    dataset_version_id: number;
    run_id: number;
    checkpoint_id: number;
    model_version_id: number;
    eval_run_id: number;
  };
};

export type EvaluationSummary = {
  filters: Record<string, number | null>;
  eval_run_count: number;
  model_version_count: number;
  output_count: number;
  failure_count: number;
  metric_summary: EvalMetricSummary[];
  runs: EvalRunSummary[];
};

export type FailureCountBucket = {
  value: string;
  count: number;
};

export type FailureLibrarySummary = {
  filters: Record<string, number | null>;
  failure_count: number;
  by_failure_type: FailureCountBucket[];
  by_severity: FailureCountBucket[];
  by_status: FailureCountBucket[];
};

export type EvalFailure = {
  eval_failure_id: number;
  eval_run_id: number;
  eval_output_id: number;
  eval_case_id: number;
  model_version_id: number;
  dataset_id: number;
  dataset_version_id: number;
  program_id: number;
  experiment_id: number;
  checkpoint_id: number;
  run_id: number;
  failure_type: string;
  severity: string;
  status: string;
  failure_reason: string;
  prompt_text: string;
  output_text: string;
  score: number;
  case_name: string;
  model_name?: string;
  model_version_name?: string;
  dataset_candidate_count: number;
  created_at: string;
};

export type EvalFailureDetail = EvalFailure & {
  scores: Record<string, number>;
  expected_topics: string[];
  required_sections: string[];
  lineage: Array<{
    lineage_step: string;
    source_type: string;
    source_id: number;
    target_type: string;
    target_id: number;
  }>;
  dataset_candidates: DatasetCandidate[];
};

export type DatasetCandidate = {
  dataset_candidate_id: number;
  eval_failure_id: number;
  source_eval_run_id: number;
  source_eval_output_id: number;
  source_model_version_id: number;
  program_id: number;
  experiment_id: number;
  target_dataset_id: number;
  failure_type: string;
  status: string;
  proposed_input_text: string;
  proposed_target_text: string;
  review_notes: string;
  source_priority: string;
  created_at: string;
  created_by_user_id: string;
  reviewed_at: string;
  reviewed_by_user_id: string;
  included_dataset_id: number;
  included_dataset_version_id: number;
  included_at: string;
};

export type DatasetIteration = {
  target_dataset_id: number;
  status: string;
  failure_type: string;
  source_model_version_id: number;
  candidate_count: number;
  included_count: number;
  first_created_at: string;
  last_created_at: string;
};

export type CreateDatasetCandidatePayload = {
  target_dataset_id: number;
  proposed_input_text: string;
  proposed_target_text: string;
  created_by_user_id?: string;
};

export type DatasetVersionFromCandidatesResponse = {
  dataset_version: {
    dataset_id: number;
    dataset_version_id: number;
    status: string;
    name?: string;
    version?: string;
  };
  candidate_count: number;
  included_candidate_ids: number[];
  iteration_manifest: {
    parent_dataset_version_id: number;
  };
};

export type RunLineageEdge = {
  lineage_step: string;
  source_type: string;
  source_id: number;
  target_type: string;
  target_id: number;
};

export type RunDetail = RunSummary & {
  run_config: {
    run_config_id: number;
    dataset_version_id: number;
    model_id: string;
    config_uri: string;
    created_at: string;
    config: Record<string, string | number>;
  };
  metric_series: RunMetric[];
  metric_summary: {
    initial_loss: number;
    final_loss: number;
    min_loss: number;
    loss_delta_percent: number;
    last_step: number;
    tokens_seen: number;
  };
  compute_summary: {
    avg_gpu_utilization: number;
    max_memory_used_gb: number;
    avg_process_memory_mb: number;
    avg_cpu_user_seconds: number;
    avg_tokens_per_second: number;
    estimated_cost_usd: number;
    hardware_note: string;
  };
  checkpoints: RunCheckpoint[];
  lineage: RunLineageEdge[];
  raw_ingest_summary: {
    raw_events_uri: string;
    ingest_source: string;
    source_priority: string;
    note: string;
  };
};

export type ResearchProgramSummary = {
  program_id: number;
  program_name: string;
  short_name: string;
  program_description: string;
  problem_statement: string;
  initiating_context: string;
  research_goal: string;
  hypothesis: string;
  research_objectives: string;
  status: string;
  research_area: string;
  current_focus: string;
  owner_name: string;
  researcher_names: string[];
  tags: string[];
  linked_dataset_ids?: number[];
  linked_dataset_versions?: Array<{ dataset_id: number; dataset_version_id: number }>;
  linked_datasets?: Array<{ dataset_id: number; dataset_version_id: number }>;
  linked_experiment_ids?: number[];
  linked_run_ids?: number[];
  notes: Array<{ note_id: number; body: string; author_name: string; created_at: string }>;
  input_source: string;
  created_at: string;
  updated_at: string;
  created_by_user_id: string;
  updated_by_user_id: string;
};

export type ResearchProgramDetail = ResearchProgramSummary & {
  ui_workflow: {
    can_update_from_ui: boolean;
    supported_actions: string[];
  };
};

export type ResearchProgramPayload = Partial<
  Pick<
    ResearchProgramSummary,
    | "program_name"
    | "short_name"
    | "program_description"
    | "problem_statement"
    | "initiating_context"
    | "research_goal"
    | "hypothesis"
    | "research_objectives"
    | "status"
    | "research_area"
    | "current_focus"
    | "owner_name"
    | "researcher_names"
    | "tags"
    | "notes"
  >
>;

export type ResearchProgramCreateResponse = {
  program_id: number;
  program_name: string;
  status: string;
  researcher_names: string[];
  created_at: string;
  updated_at: string;
};

export async function listResearchPrograms(params: Record<string, string | number | undefined> = {}): Promise<ResearchProgramSummary[]> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  const payload = await getJson<{ items: ResearchProgramSummary[] }>(`/research-programs${suffix}`);
  return payload.items;
}

export async function getResearchProgram(programId: string): Promise<ResearchProgramDetail> {
  return getJson<ResearchProgramDetail>(`/research-programs/${programId}`);
}

export async function createResearchProgram(payload: ResearchProgramPayload): Promise<ResearchProgramCreateResponse> {
  return postJson<ResearchProgramCreateResponse>("/research-programs", payload);
}

export async function updateResearchProgram(programId: string, payload: ResearchProgramPayload): Promise<ResearchProgramDetail> {
  return patchJson<ResearchProgramDetail>(`/research-programs/${programId}`, payload);
}

export async function appendResearchProgramNote(
  programId: string,
  payload: { body: string; author_name?: string },
): Promise<{ note_id: number; notes: ResearchProgramSummary["notes"]; program: ResearchProgramDetail }> {
  return postJson(`/research-programs/${programId}/notes`, payload);
}

export async function deleteResearchProgramNote(
  programId: string,
  noteId: number,
): Promise<{ deleted_note_id: number; notes: ResearchProgramSummary["notes"]; program: ResearchProgramDetail }> {
  return deleteJson(`/research-programs/${programId}/notes/${noteId}`);
}

export async function listDatasets(): Promise<DatasetSummary[]> {
  const payload = await getJson<{ items: DatasetSummary[] }>("/datasets");
  return payload.items;
}

export async function getDataset(datasetId: string): Promise<DatasetDetail> {
  return getJson<DatasetDetail>(`/datasets/${datasetId}`);
}

export async function listRuns(): Promise<RunSummary[]> {
  const payload = await getJson<{ items: RunSummary[] }>("/runs");
  return payload.items;
}

export async function getRun(runId: string): Promise<RunDetail> {
  return getJson<RunDetail>(`/runs/${runId}`);
}

export async function searchCheckpoints(params: Record<string, string | number | undefined>): Promise<CheckpointSearchResult[]> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  const payload = await getJson<{ items: CheckpointSearchResult[] }>(`/checkpoints?${query.toString()}`);
  return payload.items;
}

export async function listModels(): Promise<ModelVersionSummary[]> {
  const payload = await getJson<{ items: ModelVersionSummary[] }>("/models");
  return payload.items;
}

export async function getModel(modelVersionId: string): Promise<ModelVersionDetail> {
  return getJson<ModelVersionDetail>(`/models/${modelVersionId}`);
}

export async function registerModelFromCheckpoint(payload: RegisterModelPayload): Promise<RegisterModelResponse> {
  return postJson<RegisterModelResponse>("/models/register-from-checkpoint", payload);
}

export async function getEvaluationSummary(
  params: Record<string, string | number | undefined> = {},
): Promise<EvaluationSummary> {
  const suffix = querySuffix(params);
  return getJson<EvaluationSummary>(`/evaluations/summary${suffix}`);
}

export async function listEvalRuns(
  params: Record<string, string | number | undefined> = {},
): Promise<EvalRunSummary[]> {
  const suffix = querySuffix(params);
  const payload = await getJson<{ items: EvalRunSummary[] }>(`/eval-runs${suffix}`);
  return payload.items;
}

export async function getFailureLibrarySummary(
  params: Record<string, string | number | undefined> = {},
): Promise<FailureLibrarySummary> {
  const suffix = querySuffix(params);
  return getJson<FailureLibrarySummary>(`/failure-library/summary${suffix}`);
}

export async function listFailures(
  params: Record<string, string | number | undefined> = {},
): Promise<EvalFailure[]> {
  const suffix = querySuffix(params);
  const payload = await getJson<{ items: EvalFailure[] }>(`/failure-library${suffix}`);
  return payload.items;
}

export async function getFailure(evalFailureId: string): Promise<EvalFailureDetail> {
  return getJson<EvalFailureDetail>(`/failure-library/${evalFailureId}`);
}

export async function createDatasetCandidateFromFailure(
  evalFailureId: string | number,
  payload: CreateDatasetCandidatePayload,
): Promise<DatasetCandidate> {
  return postJson<DatasetCandidate>(`/eval-failures/${evalFailureId}/dataset-candidate`, payload);
}

export async function listDatasetCandidates(
  params: Record<string, string | number | undefined> = {},
): Promise<DatasetCandidate[]> {
  const suffix = querySuffix(params);
  const payload = await getJson<{ items: DatasetCandidate[] }>(`/dataset-candidates${suffix}`);
  return payload.items;
}

export async function reviewDatasetCandidate(
  candidateId: string | number,
  payload: { status: string; review_notes?: string; reviewed_by_user_id?: string },
): Promise<DatasetCandidate> {
  return patchJson<DatasetCandidate>(`/dataset-candidates/${candidateId}`, payload);
}

export async function listDatasetIterations(
  params: Record<string, string | number | undefined> = {},
): Promise<DatasetIteration[]> {
  const suffix = querySuffix(params);
  const payload = await getJson<{ items: DatasetIteration[] }>(`/dataset-iterations${suffix}`);
  return payload.items;
}

export async function createDatasetVersionFromCandidates(
  datasetId: string | number,
  payload: {
    candidate_ids?: number[];
    candidate_status?: string;
    version_notes?: string;
    created_by_user_id?: string;
  },
): Promise<DatasetVersionFromCandidatesResponse> {
  return postJson<DatasetVersionFromCandidatesResponse>(`/datasets/${datasetId}/versions/from-candidates`, payload);
}

function querySuffix(params: Record<string, string | number | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  }
  return query.toString() ? `?${query.toString()}` : "";
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: JSON.stringify(payload),
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function patchJson<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: JSON.stringify(payload),
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
    },
    method: "PATCH",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}
