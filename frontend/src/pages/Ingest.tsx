import { useEffect, useMemo, useState } from 'react';
import {
  demoBatch,
  getIngestBatch,
  ingestSummary,
  listIngestBatches,
  runIngestBatch,
} from '../api/ingest';
import type { IngestBatchIn, IngestBatchResult, IngestRecord } from '../api/ingest';
import { useAsync } from '../hooks/useAsync';
import { useAuthStore } from '../stores/authStore';
import { can } from '../constants/roles';
import { SectionHead } from '../components/common/SectionHead';
import { MetricCard } from '../components/common/MetricCard';
import { LoadingBlock } from '../components/common/LoadingBlock';
import { ErrorBlock } from '../components/common/ErrorBlock';
import { EmptyState } from '../components/common/EmptyState';
import { StatusPill } from '../components/common/StatusPill';
import { kYuan, datetime } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';

const ACTION_TONE: Record<string, string> = {
  new: 'tag-sage',
  merged: 'tag-indigo',
  ignored: 'tag',
  failed: 'tag-rust',
};

const ACTION_FILTERS = ['', 'new', 'merged', 'ignored', 'failed'] as const;

export function IngestPage() {
  const user = useAuthStore((state) => state.user);
  const summary = useAsync(ingestSummary, []);
  const batches = useAsync(listIngestBatches, []);
  const [result, setResult] = useState<IngestBatchResult | null>(null);
  const [action, setAction] = useState<string>('');
  const [conflictOnly, setConflictOnly] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const latest = summary.data?.latest_batch || null;

  useEffect(() => {
    if (result || !latest) return;
    getIngestBatch(latest.id).then(setResult).catch(() => undefined);
  }, [latest, result]);

  async function handleDemoRun() {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const payload: IngestBatchIn = await demoBatch();
      const response = await runIngestBatch(payload);
      setResult(response);
      setNotice(
        response.duplicate_batch
          ? `批次 ${response.batch_key} 已存在，直接返回首次结果（重复运行未新增岗位）`
          : `批次 ${response.batch_key} 完成：新增 ${response.new_count} / 合并 ${response.merged_count} / 忽略 ${response.ignored_count} / 失败 ${response.failed_count}`,
      );
      summary.reload();
      batches.reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function openBatch(id: number) {
    setError('');
    setNotice('');
    try {
      setResult(await getIngestBatch(id));
      setAction('');
      setConflictOnly(false);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const records = useMemo(() => {
    if (!result) return [];
    return result.records.filter((record) => {
      if (action && record.action !== action) return false;
      if (conflictOnly && !record.conflict_kind) return false;
      return true;
    });
  }, [result, action, conflictOnly]);

  const counts = {
    new: result?.new_count ?? summary.data?.new ?? 0,
    merged: result?.merged_count ?? summary.data?.merged ?? 0,
    ignored: result?.ignored_count ?? summary.data?.ignored ?? 0,
    failed: result?.failed_count ?? summary.data?.failed ?? 0,
  };

  return (
    <div className="drawer-in">
      <SectionHead
        eyebrow="07 / INGEST"
        title="采集入库 · 同岗位只留最新薪酬"
        aside={
          <>
            <span className="tag tag-indigo">自然键：公司 + 城市 + 职位</span>
            <button
              className="btn btn-sm btn-primary"
              data-testid="ingest-run-demo"
              disabled={!can(user?.role, 'ingest:run') || busy}
              onClick={handleDemoRun}
              title={can(user?.role, 'ingest:run') ? '投递五渠道重送演示批' : '当前角色无采集入库权限'}
            >
              {busy ? '入库中…' : '运行五渠道演示批'}
            </button>
          </>
        }
      />

      <div className="grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', marginBottom: '0.9rem' }}>
        <MetricCard label="新增岗位" value={counts.new} hint="首次出现的自然键（当前批次）" tone="sage" />
        <MetricCard label="合并" value={counts.merged} hint="新版本覆盖 / 迟到旧版本留说明" tone="indigo" />
        <MetricCard label="忽略" value={counts.ignored} hint="external_id 已入湖 / 人工修正保护" />
        <MetricCard label="失败（隔离）" value={counts.failed} hint="面议 / 无法解析 / 缺字段 / 兼职" tone="copper" />
      </div>

      <div
        className="card"
        style={{ padding: '0.7rem 1rem', marginBottom: '0.9rem', display: 'flex', gap: '1.2rem', flexWrap: 'wrap', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}
      >
        <span>批次 <strong>{summary.data?.batches ?? '—'}</strong></span>
        <span>冲突说明 <strong>{summary.data?.conflicts ?? '—'}</strong></span>
        <span>异常隔离 raw <strong>{summary.data?.quarantined_raws ?? '—'}</strong></span>
        <span>重复折叠 raw <strong>{summary.data?.duplicate_folded_raws ?? '—'}</strong></span>
        <span>最近批次 {latest ? `${latest.name || latest.batch_key} · ${datetime(latest.finished_at)}` : '—'}</span>
      </div>

      {notice ? <p style={{ color: 'var(--sage)', fontSize: 'var(--fs-small)' }} data-testid="ingest-notice">{notice}</p> : null}
      {error ? <p style={{ color: 'var(--rust)', fontSize: 'var(--fs-small)' }}>{error}</p> : null}

      <div className="grid" style={{ gridTemplateColumns: '16rem minmax(0, 1fr)', alignItems: 'start' }}>
        <div className="card" style={{ padding: '0.5rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)', padding: '0.35rem 0.4rem' }}>
            批次历史
          </div>
          {batches.loading ? <LoadingBlock /> : null}
          {!batches.loading && (batches.data?.length || 0) === 0 ? (
            <p style={{ padding: '0.3rem 0.4rem', fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
              还没有采集批次，点右上角运行演示批。
            </p>
          ) : null}
          {(batches.data || []).map((batch) => {
            const active = result?.id === batch.id;
            return (
              <button
                key={batch.id}
                data-testid={`ingest-batch-${batch.id}`}
                onClick={() => openBatch(batch.id)}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '0.38rem 0.4rem',
                  marginBottom: 2,
                  border: 'none',
                  borderRadius: 2,
                  background: active ? 'var(--indigo)' : 'transparent',
                  color: active ? 'var(--paper-card)' : 'var(--ink)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--fs-micro)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: active ? 600 : 500 }}>#{batch.id} {batch.name || batch.batch_key}</div>
                <div style={{ opacity: 0.8, marginTop: 2 }}>
                  {batch.total_count} 条 · 新 {batch.new_count} / 合 {batch.merged_count} / 忽 {batch.ignored_count} / 失 {batch.failed_count}
                </div>
                <div style={{ opacity: 0.65 }}>{datetime(batch.started_at)}</div>
              </button>
            );
          })}
        </div>

        <div>
          {summary.loading && !result ? <LoadingBlock /> : null}
          {summary.error ? <ErrorBlock message={summary.error} onRetry={summary.reload} /> : null}
          {!result && !summary.loading ? (
            <EmptyState title="还没有可展示的采集批次" hint="运行五渠道演示批：同一岗位 5 个来源 + 迟到旧版本 + 异常隔离" />
          ) : null}

          {result ? (
            <>
              <div className="card" style={{ padding: '0.85rem 1rem', marginBottom: '0.8rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'baseline' }}>
                  <h3 style={{ fontSize: '1.05rem' }}>{result.name || result.batch_key}</h3>
                  <span className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
                    {result.batch_key} · {result.status}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.45rem', flexWrap: 'wrap' }}>
                  <span className="tag tag-sage">新增 {result.new_count}</span>
                  <span className="tag tag-indigo">合并 {result.merged_count}</span>
                  <span className="tag">忽略 {result.ignored_count}</span>
                  <span className="tag tag-rust">失败 {result.failed_count}</span>
                  <span className="tag">{result.source_count} 个来源</span>
                  <span className="tag">{result.created_by}</span>
                </div>
                <p style={{ margin: '0.45rem 0 0', fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
                  合并前来源指被覆盖的旧版本来源，合并后来源指最终保留的版本来源；迟到旧版本不会覆盖最新薪酬。
                </p>
              </div>

              <div className="card" style={{ padding: '0.2rem 0.3rem', marginBottom: '0.8rem' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>采集源</th>
                      <th>投递</th>
                      <th>新增</th>
                      <th>合并</th>
                      <th>忽略</th>
                      <th>失败</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.source_breakdown.map((row) => (
                      <tr key={row.source_name} style={{ cursor: 'default' }}>
                        <td>{row.source_name}</td>
                        <td className="mono">{row.total}</td>
                        <td className="mono" style={{ color: 'var(--sage)' }}>{row.new}</td>
                        <td className="mono" style={{ color: 'var(--indigo)' }}>{row.merged}</td>
                        <td className="mono">{row.ignored}</td>
                        <td className="mono" style={{ color: 'var(--rust)' }}>{row.failed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center', marginBottom: '0.55rem' }}>
                {ACTION_FILTERS.map((tab) => (
                  <button
                    key={tab || 'all'}
                    className={`btn btn-sm ${action === tab ? 'btn-primary' : 'btn-ghost'}`}
                    data-testid={`ingest-filter-${tab || 'all'}`}
                    onClick={() => setAction(tab)}
                  >
                    {tab ? result.records.find((record) => record.action === tab)?.action_label || tab : '全部'} {tab ? result.records.filter((record) => record.action === tab).length : result.records.length}
                  </button>
                ))}
                <label className="tag" style={{ cursor: 'pointer', display: 'inline-flex', gap: '0.3rem', alignItems: 'center' }}>
                  <input
                    type="checkbox"
                    checked={conflictOnly}
                    onChange={(event) => setConflictOnly(event.target.checked)}
                  />
                  只看冲突说明
                </label>
              </div>

              {records.length === 0 ? (
                <EmptyState title="该筛选下没有记录" hint="换一个动作或取消「只看冲突说明」" />
              ) : (
                <div className="card" style={{ padding: '0.2rem 0.3rem' }}>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th>动作</th>
                        <th>岗位 / 原始薪资</th>
                        <th>合并前来源 → 合并后来源</th>
                        <th>薪酬 前 → 后</th>
                        <th>说明</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.map((record) => (
                        <IngestRow key={record.id} record={record} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function IngestRow({ record }: { record: IngestRecord }) {
  const before =
    record.before_salary_min !== null && record.before_salary_max !== null
      ? `${kYuan(record.before_salary_min)}-${kYuan(record.before_salary_max)}`
      : '—';
  const incoming =
    record.incoming_salary_min !== null && record.incoming_salary_max !== null
      ? `${kYuan(record.incoming_salary_min)}-${kYuan(record.incoming_salary_max)}`
      : '—';
  return (
    <tr style={{ cursor: 'default' }} data-testid={`ingest-row-${record.id}`}>
      <td className="mono" style={{ fontSize: 'var(--fs-micro)' }}>{record.line_no}</td>
      <td>
        <span className={`tag ${ACTION_TONE[record.action] || 'tag'}`}>{record.action_label || record.action}</span>
        {record.conflict_kind ? (
          <div style={{ marginTop: 3 }}>
            <span className="tag tag-copper" title={record.conflict_label}>{record.conflict_label || record.conflict_kind}</span>
          </div>
        ) : null}
      </td>
      <td>
        <div>{record.canonical_title || record.company || '—'}</div>
        <div className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
          {record.company} · {record.city} · {record.salary_raw || '缺薪资'} · {record.external_id || '缺 external_id'}
        </div>
      </td>
      <td className="mono" style={{ fontSize: 'var(--fs-micro)' }}>
        {record.before_source_name
          ? <>{record.before_source_name}<br /><span style={{ color: 'var(--ink-soft)' }}>→ {record.after_source_name || '—'}</span></>
          : record.after_source_name || '—'}
      </td>
      <td className="mono" style={{ fontSize: 'var(--fs-micro)' }}>
        {before}
        <br />
        <span style={{ color: record.action === 'merged' ? 'var(--indigo)' : 'var(--ink-soft)' }}>→ {incoming}</span>
      </td>
      <td style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)', maxWidth: 360 }}>{record.note}</td>
    </tr>
  );
}
