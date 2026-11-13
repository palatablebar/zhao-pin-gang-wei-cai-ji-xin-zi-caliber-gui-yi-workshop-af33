import type { ReactNode } from 'react';

export function SectionHead({ eyebrow, title, aside }: { eyebrow: string; title: string; aside?: ReactNode }) {
  return (
    <div className="section-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 style={{ fontSize: 'var(--fs-title)', marginTop: '0.15rem' }}>{title}</h1>
      </div>
      {aside ? <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>{aside}</div> : null}
    </div>
  );
}
