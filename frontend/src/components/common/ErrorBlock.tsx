export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card" style={{ padding: '1.2rem', borderColor: 'var(--rust)' }}>
      <div className="mono" style={{ color: 'var(--rust)', fontSize: 'var(--fs-micro)', letterSpacing: '0.15em' }}>
        REQUEST FAILED
      </div>
      <p style={{ margin: '0.5rem 0 0.8rem' }}>{message}</p>
      {onRetry ? (
        <button className="btn btn-sm" onClick={onRetry}>
          重试
        </button>
      ) : null}
    </div>
  );
}
