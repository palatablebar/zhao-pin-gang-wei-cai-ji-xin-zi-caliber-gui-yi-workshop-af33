import { request } from './client';
import type { Source } from '../types/models';

export function listSources(): Promise<Source[]> {
  return request<Source[]>('/sources');
}

export function syncSource(id: number): Promise<{ task_id: string; source_id: number; message: string }> {
  return request(`/sources/${id}/sync`, { method: 'POST' });
}
