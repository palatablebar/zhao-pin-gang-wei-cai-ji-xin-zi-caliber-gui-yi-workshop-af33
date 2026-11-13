export function LoadingBlock({ label = '正在翻档案…' }: { label?: string }) {
  return (
    <div style={{ padding: '1.6rem 0', color: 'var(--ink-soft)', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-small)' }}>
      <span style={{ letterSpacing: '0.12em' }}>{label}</span>
    </div>
  );
}
