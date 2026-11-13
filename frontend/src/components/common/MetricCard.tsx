import type { ReactNode } from 'react';

export function MetricCard({ label, value, hint, tone = 'ink' }: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: 'ink' | 'copper' | 'indigo' | 'sage';
}) {
  const color =
    tone === 'copper' ? 'var(--copper)' : tone === 'indigo' ? 'var(--indigo)' : tone === 'sage' ? 'var(--sage)' : 'var(--ink)';
  return (
    <div className="card" style={{ padding: '0.85rem 1rem', minWidth: 0 }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)' }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.6rem', color, lineHeight: 1.15, marginTop: '0.25rem' }}>
        {value}
      </div>
      {hint ? (
        <div style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)', marginTop: '0.2rem' }}>{hint}</div>
      ) : null}
    </div>
  );
}
