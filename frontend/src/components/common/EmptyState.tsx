import type { ReactNode } from 'react';

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div
      className="card"
      style={{ padding: '2.4rem 1.4rem', textAlign: 'center', borderStyle: 'dashed' }}
    >
      <div style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.2em', color: 'var(--copper)' }}>EMPTY DRAWER</div>
      <h3 style={{ margin: '0.6rem 0 0.3rem', fontSize: 'var(--fs-title)' }}>{title}</h3>
      {hint ? <p style={{ margin: 0, color: 'var(--ink-soft)' }}>{hint}</p> : null}
      {action ? <div style={{ marginTop: '1rem' }}>{action}</div> : null}
    </div>
  );
}
