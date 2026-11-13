export function yuan(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return `¥${value.toLocaleString('zh-CN')}`;
}

export function kYuan(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  const k = value / 1000;
  return `${Number.isInteger(k) ? k.toFixed(0) : k.toFixed(1)}K`;
}

export function pct(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return '—';
  return `${value.toFixed(digits)}%`;
}

export function datetime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

export function shortDate(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
