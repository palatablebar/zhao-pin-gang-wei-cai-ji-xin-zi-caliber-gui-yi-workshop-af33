import { BAND_CEILING, BAND_FLOOR, bandPosition } from '../../utils/salary';
import { kYuan } from '../../utils/format';

interface Props {
  min: number | null;
  max: number | null;
  median?: number | null;
  annualMonths?: number;
  unit?: string;
  explicitFloor?: number;
  explicitCeiling?: number;
  height?: number;
}

/** 细线刻度尺式薪资区间条：底尺 + 区间段 + 中位数刻度。 */
export function SalaryBandBar({
  min,
  max,
  median,
  annualMonths = 12,
  unit = 'monthly',
  explicitFloor,
  explicitCeiling,
  height = 30,
}: Props) {
  const floor = explicitFloor ?? BAND_FLOOR;
  const ceiling = explicitCeiling ?? BAND_CEILING;
  const hasRange = min !== null && max !== null && min !== undefined && max !== undefined;
  const left = hasRange ? bandPosition(min as number, floor, ceiling) : 0;
  const right = hasRange ? bandPosition(max as number, floor, ceiling) : 0;
  const mid = median !== null && median !== undefined ? bandPosition(median, floor, ceiling) : null;

  return (
    <div style={{ minWidth: 150 }}>
      <div style={{ position: 'relative', height, marginBottom: '0.15rem' }}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: '50%',
            height: 1,
            background: 'var(--paper-line)',
          }}
        />
        {[0, 25, 50, 75, 100].map((tick) => (
          <div
            key={tick}
            style={{
              position: 'absolute',
              left: `${tick}%`,
              top: '38%',
              width: 1,
              height: 7,
              background: 'var(--paper-line)',
            }}
          />
        ))}
        {hasRange ? (
          <>
            <div
              style={{
                position: 'absolute',
                left: `${left}%`,
                width: `${Math.max(right - left, 1.5)}%`,
                top: 'calc(50% - 5px)',
                height: 10,
                background: 'color-mix(in oklch, var(--copper) 78%, var(--paper-card))',
                border: '1px solid var(--copper)',
                borderRadius: 1,
              }}
            />
            {mid !== null ? (
              <div
                title={`中位数 ${kYuan(median)}`}
                style={{
                  position: 'absolute',
                  left: `${mid}%`,
                  top: 'calc(50% - 8px)',
                  width: 2,
                  height: 16,
                  background: 'var(--indigo)',
                  transform: 'translateX(-1px)',
                }}
              />
            ) : null}
          </>
        ) : (
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: 'calc(50% - 2px)',
              width: 14,
              height: 4,
              border: '1px dashed var(--ink-soft)',
              transform: 'translateX(-50%)',
            }}
          />
        )}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
        {hasRange ? `${kYuan(min)} – ${kYuan(max)}${annualMonths !== 12 ? ` · ${annualMonths}薪` : ''}` : '面议'}
        {unit === 'annual' ? ' · 年薪制' : ''}
      </div>
    </div>
  );
}
