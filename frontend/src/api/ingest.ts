import { request } from './client';

export interface IngestItemIn {
  source_id?: number;
  source_name?: string;
  external_id: string;
  title: string;
  salary_raw?: string;
  city?: string;
  company?: string;
  experience_raw?: string;
  employment_type_raw?: string;
  published_at?: string;
}

export interface IngestBatchIn {
  batch_key: string;
  name?: string;
  note?: string;
  items: IngestItemIn[];
}

export interface IngestBatch {
  id: number;
  batch_key: string;
  name: string;
  status: string;
  total_count: number;
  new_count: number;
  merged_count: number;
  ignored_count: number;
  failed_count: number;
  source_count: number;
  created_by: string;
  note: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

export interface IngestRecord {
  id: number;
  batch_id: number;
  line_no: number;
  source_id: number | null;
  source_name: string;
  external_id: string;
  raw_id: number | null;
  posting_id: number | null;
  action: 'new' | 'merged' | 'ignored' | 'failed' | string;
  action_label: string;
  reason: string;
  note: string;
  conflict_kind: string;
  conflict_label: string;
  company: string;
  city: string;
  canonical_title: string;
  salary_raw: string;
  salary_median: number | null;
  published_at: string | null;
  before_source_id: number | null;
  before_source_name: string;
  after_source_id: number | null;
  after_source_name: string;
  before_salary_min: number | null;
  before_salary_max: number | null;
  incoming_salary_min: number | null;
  incoming_salary_max: number | null;
  created_at: string | null;
}

export interface SourceBreakdown {
  source_name: string;
  total: number;
  new: number;
  merged: number;
  ignored: number;
  failed: number;
}

export interface IngestBatchResult extends IngestBatch {
  duplicate_batch: boolean;
  records: IngestRecord[];
  source_breakdown: SourceBreakdown[];
}

export interface IngestSummary {
  batches: number;
  new: number;
  merged: number;
  ignored: number;
  failed: number;
  conflicts: number;
  quarantined_raws: number;
  duplicate_folded_raws: number;
  latest_batch: IngestBatch | null;
  action_labels: Record<string, string>;
  conflict_labels: Record<string, string>;
  quarantine_status: string;
  quarantine_status_label: string;
}

export function ingestSummary(): Promise<IngestSummary> {
  return request<IngestSummary>('/ingest/summary');
}

export function listIngestBatches(): Promise<IngestBatch[]> {
  return request<IngestBatch[]>('/ingest/batches');
}

export function getIngestBatch(id: number): Promise<IngestBatchResult> {
  return request<IngestBatchResult>(`/ingest/batches/${id}`);
}

export function runIngestBatch(payload: IngestBatchIn): Promise<IngestBatchResult> {
  return request<IngestBatchResult>('/ingest/batches', { method: 'POST', body: payload });
}

export function demoBatch(): Promise<IngestBatchIn> {
  return request<IngestBatchIn>('/ingest/demo-batch');
}
