const TONE: Record<string, string> = {
  parsed: 'tag-sage',
  corrected: 'tag-indigo',
  needs_review: 'tag-copper',
  failed: 'tag-rust',
  duplicate: 'tag',
  invalid: 'tag-rust',
  open: 'tag-copper',
  disposed: 'tag-sage',
  ignored: 'tag',
  idle: 'tag-sage',
  queued: 'tag-copper',
  running: 'tag-copper',
  failed_sync: 'tag-rust',
  published: 'tag-indigo',
  draft: 'tag',
};

export function StatusPill({ status, label }: { status: string; label?: string }) {
  return <span className={`tag ${TONE[status] || 'tag'}`}>{label || status}</span>;
}
