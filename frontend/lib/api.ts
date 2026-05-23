const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DatasetSummary = {
  dataset_id: number;
  dataset_version_id: number;
  name: string;
  source_dataset_name: string;
  source_url: string;
  task_type: string;
  category: string;
  source_label: string;
  record_count: number;
  quality_status: string;
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

export type DatasetDetail = DatasetSummary & {
  description: string;
  quality_metrics: QualityMetric[];
  schema_profile: SchemaField[];
  lineage: DatasetLineage[];
  sample_records: DatasetRecord[];
};

export async function listDatasets(): Promise<DatasetSummary[]> {
  const payload = await getJson<{ items: DatasetSummary[] }>("/datasets");
  return payload.items;
}

export async function getDataset(datasetId: string): Promise<DatasetDetail> {
  return getJson<DatasetDetail>(`/datasets/${datasetId}`);
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
