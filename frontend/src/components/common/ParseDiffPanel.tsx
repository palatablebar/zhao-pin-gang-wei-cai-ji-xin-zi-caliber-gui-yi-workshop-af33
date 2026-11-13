import type { RawDetail } from '../../types/models';
import { kYuan } from '../../utils/format';
import { QUALITY_LABELS } from '../../constants/enums';

function Cell({ label, raw, normalized }: { label: string; raw: string; normalized: string }) {
  const changed = raw !== normalized;
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '4.6rem 1fr 1fr',
        gap: '0.6rem',
        padding: '0.42rem 0',
        borderBottom: '1px dashed var(--paper-line)',
        fontSize: 'var(--fs-small)',
      }}
    >
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)', letterSpacing: '0.06em' }}>
        {label}
      </div>
      <div style={{ color: 'var(--ink-soft)', wordBreak: 'break-all' }}>{raw}</div>
      <div style={{ color: changed ? 'var(--indigo)' : 'var(--ink)', fontFamily: changed ? 'var(--font-mono)' : 'inherit' }}>
        {normalized}
      </div>
    </div>
  );
}

/** raw 原值 vs 归一结果 对照面板（原始队列 + 质量门禁共用）。 */
export function ParseDiffPanel({ detail, compact = false }: { detail: RawDetail; compact?: boolean }) {
  const preview = detail.current;
  if (!preview) return null;
  const salaryText =
    preview.salary_min === null || preview.salary_max === null
      ? preview.status === 'negotiable'
        ? '面议（null）'
        : `解析失败（${preview.reason_code}）`
      : `${kYuan(preview.salary_min)} – ${kYuan(preview.salary_max)} · 中位 ${kYuan(preview.salary_median)}`;
  return (
    <div className={compact ? '' : 'drawer-in'}>
      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
        <span className="tag tag-indigo">规则 {preview.version}</span>
        <span className="tag tag-copper">{preview.reason_code}</span>
        {preview.flags.map((flag) => (
          <span key={flag} className="tag tag-rust">{QUALITY_LABELS[flag] || flag}</span>
        ))}
      </div>
      <Cell label="标题" raw={detail.title_raw} normalized={preview.canonical_title} />
      <Cell label="薪资" raw={detail.salary_raw} normalized={salaryText} />
      <Cell label="城市" raw={detail.city_raw} normalized={preview.city || detail.city_raw} />
      <div style={{ display: 'grid', gridTemplateColumns: '4.6rem 1fr 1fr', gap: '0.6rem', padding: '0.42rem 0', borderBottom: '1px dashed var(--paper-line)', fontSize: 'var(--fs-small)' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>职能/职级</div>
        <div style={{ color: 'var(--ink-soft)' }}>{detail.experience_raw} · {detail.employment_type_raw}</div>
        <div style={{ fontFamily: 'var(--font-mono)' }}>
          {preview.function_type} / {preview.seniority}
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '4.6rem 1fr 1fr', gap: '0.6rem', padding: '0.42rem 0', fontSize: 'var(--fs-small)' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>口径</div>
        <div style={{ color: 'var(--ink-soft)' }}>annual_months / confidence</div>
        <div style={{ fontFamily: 'var(--font-mono)' }}>
          {preview.annual_months} 薪 · {preview.confidence.toFixed(2)} · 标题 {preview.title_confidence.toFixed(2)}
        </div>
      </div>
      <div style={{ marginTop: '0.6rem', display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
        {preview.matched_terms.map((term) => (
          <span key={term} className="tag">{term}</span>
        ))}
        {preview.matched_rules.map((rule) => (
          <span key={rule} className="tag tag-indigo">{rule}</span>
        ))}
      </div>
    </div>
  );
}
