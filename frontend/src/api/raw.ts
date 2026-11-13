import { request } from './client';
import type { Paged, RawDetail, RawPosting } from '../types/models';

export interface RawFilters {
  status?: string;
  city?: string;
  q?: string;
  source_id?: number;
  page?: number;
  size?: number;
}

export function listRaw(filters: RawFilters): Promise<Paged<RawPosting>> {
  return request<Paged<RawPosting>>('/raw', { params: { ...filters } });
}

export function statusCounts(): Promise<{ status: string; label: string; count: number }[]> {
  return request('/raw/status-counts');
}

export function getRaw(id: number): Promise<RawDetail> {
  return request<RawDetail>(`/raw/${id}`);
}

export function correctRaw(id: number, payload: Record<string, unknown>): Promise<RawDetail> {
  return request<RawDetail>(`/raw/${id}/correct`, { method: 'POST', body: payload });
}
