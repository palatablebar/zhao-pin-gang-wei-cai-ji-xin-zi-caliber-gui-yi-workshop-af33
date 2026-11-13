import type { ApiErrorPayload } from '../types/api';

const BASE = '/api';

export class ApiError extends Error {
  status: number;
  code: string;
  detail?: string;

  constructor(status: number, payload: ApiErrorPayload) {
    super(payload.message || `HTTP ${status}`);
    this.status = status;
    this.code = payload.code || 'ERROR';
    this.detail = payload.detail;
  }
}

function token(): string | null {
  return localStorage.getItem('jobnorm.token');
}

export function setToken(value: string | null): void {
  if (value) localStorage.setItem('jobnorm.token', value);
  else localStorage.removeItem('jobnorm.token');
}

function buildQuery(params?: Record<string, string | number | boolean | null | undefined>): string {
  if (!params) return '';
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.set(key, String(value));
  });
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

async function parseError(res: Response): Promise<ApiError> {
  let payload: ApiErrorPayload = { code: 'HTTP_ERROR', message: `HTTP ${res.status}` };
  try {
    payload = (await res.json()) as ApiErrorPayload;
  } catch {
    // 非 JSON 错误（例如 Nginx 502）
  }
  return new ApiError(res.status, payload);
}

export async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; params?: Record<string, string | number | boolean | null | undefined> } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const current = token();
  if (current) headers.Authorization = `Bearer ${current}`;
  if (options.body !== undefined) headers['Content-Type'] = 'application/json';
  const res = await fetch(`${BASE}${path}${buildQuery(options.params)}`, {
    method: options.method || 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function downloadCsv(path: string, filename: string, params?: Record<string, string | number | boolean | null | undefined>): Promise<void> {
  const headers: Record<string, string> = {};
  const current = token();
  if (current) headers.Authorization = `Bearer ${current}`;
  const res = await fetch(`${BASE}${path}${buildQuery(params)}`, { headers });
  if (!res.ok) throw await parseError(res);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
