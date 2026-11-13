export interface ApiErrorPayload {
  code: string;
  message: string;
  detail?: string;
  trace_id?: string | null;
}

export type ListParams = Record<string, string | number | boolean | null | undefined>;
