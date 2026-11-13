import { request } from './client';
import type { ParseRule, ReparseResult, TrialResult } from '../types/models';

export function listRules(): Promise<ParseRule[]> {
  return request<ParseRule[]>('/rules');
}

export function trial(version: string): Promise<TrialResult> {
  return request<TrialResult>(`/rules/${version}/trial`);
}

export function reparse(version: string): Promise<ReparseResult> {
  return request<ReparseResult>(`/rules/${version}/reparse`, { method: 'POST' });
}

export function activate(version: string): Promise<{ version: string; active: boolean; rules: number }> {
  return request(`/rules/${version}/activate`, { method: 'POST' });
}

export function titleMerge(): Promise<{ merged_count: number; threshold: number; clusters: unknown[] }> {
  return request('/rules/title-merge');
}
