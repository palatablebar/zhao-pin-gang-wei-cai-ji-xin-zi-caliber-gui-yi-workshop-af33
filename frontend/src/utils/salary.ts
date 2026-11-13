import { kYuan } from './format';

/** 薪资区间文本：15-25K·14薪 → "¥15,000 – ¥25,000 · 14薪"。 */
export function salaryRangeText(
  min: number | null | undefined,
  max: number | null | undefined,
  annualMonths = 12,
  unit = 'monthly',
): string {
  if (min === null || min === undefined || max === null || max === undefined) return '面议 / 待补';
  const base = `${kYuan(min)}–${kYuan(max)}`;
  const months = annualMonths && annualMonths !== 12 ? ` · ${annualMonths}薪` : '';
  const unitLabel = unit === 'annual' ? '（年薪制折算）' : '';
  return `${base}${months}${unitLabel}`;
}

/** 区间条位置（0-100），用于 SalaryBandBar。 */
export function bandPosition(value: number, floor: number, ceiling: number): number {
  if (ceiling <= floor) return 0;
  const clamped = Math.min(ceiling, Math.max(floor, value));
  return ((clamped - floor) / (ceiling - floor)) * 100;
}

export const BAND_FLOOR = 3000;
export const BAND_CEILING = 60000;
