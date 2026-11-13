import { request } from './client';
import type { QualityPage } from '../types/models';

export function listQuality(params: { flag?: string; status?: string; page?: number; size?: number }): Promise<QualityPage> {
  return request<QualityPage>('/quality', { params: { ...params } });
}

export function dispose(postingId: number, action: 'disposed' | 'ignored', note: string): Promise<{ posting_id: number; quality_status: string; note: string }> {
  return request(`/quality/${postingId}/dispose`, { method: 'POST', body: { action, note } });
}
