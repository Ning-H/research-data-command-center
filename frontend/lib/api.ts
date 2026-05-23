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
    avg_tokens_per_second: number;
    estimated_cost_usd: number;
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

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}
