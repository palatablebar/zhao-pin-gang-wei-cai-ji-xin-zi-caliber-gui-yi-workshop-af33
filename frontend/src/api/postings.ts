import { downloadCsv, request } from './client';
import type { Paged, Posting, PostingStats } from '../types/models';

export interface PostingFilters {
  city?: string;
  function_type?: string;
  seniority?: string;
  unit?: string;
  q?: string;
  flagged?: boolean;
  corrected?: boolean;
  page?: number;
  size?: number;
}

export function listPostings(filters: PostingFilters): Promise<Paged<Posting>> {
  return request<Paged<Posting>>('/postings', { params: { ...filters } });
}

export function postingStats(): Promise<PostingStats> {
  return request<PostingStats>('/postings/stats');
}

export function getPosting(id: number): Promise<Posting> {
  return request<Posting>(`/postings/${id}`);
}

export function correctPosting(id: number, payload: Record<string, unknown>): Promise<Posting> {
  return request<Posting>(`/postings/${id}/correct`, { method: 'PATCH', body: payload });
}

export function exportPostings(city?: string, functionType?: string): Promise<void> {
  return downloadCsv('/postings/export.csv', 'jobnorm-postings.csv', { city, function_type: functionType });
}
