import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { getRaw, listRaw, statusCounts } from '../api/raw';
import { listSources } from '../api/sources';
import { correctRaw } from '../api/raw';
import { useAsync } from '../hooks/useAsync';
import { useDebounced } from '../hooks/useDebounced';
import { useAuthStore } from '../stores/authStore';
import { can } from '../constants/roles';
import { RAW_STATUS_LABELS, QUALITY_LABELS } from '../constants/enums';
import { SectionHead } from '../components/common/SectionHead';
import { StatusPill } from '../components/common/StatusPill';
import { LoadingBlock } from '../components/common/LoadingBlock';
import { ErrorBlock } from '../components/common/ErrorBlock';
import { EmptyState } from '../components/common/EmptyState';
import { ParseDiffPanel } from '../components/common/ParseDiffPanel';
import type { RawDetail } from '../types/models';
import { datetime } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';

const STATUS_TABS = ['', 'failed', 'needs_review', 'parsed', 'duplicate', 'invalid', 'corrected'];

export function RawQueuePage() {
  const user = useAuthStore((state) => state.user);
  const [status, setStatus] = useState('failed');
  const [sourceId, setSourceId] = useState<number | ''>('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const debouncedQuery = useDebounced(query);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<RawDetail | null>(null);
  const [detailError, setDetailError] = useState('');
  const [notice, setNotice] = useState('');

  const counts = useAsync(statusCounts, []);
  const sources = useAsync(listSources, []);
  const list = useAsync(
    () => listRaw({ status: status || undefined, source_id: sourceId || undefined, q: debouncedQuery || undefined, page, size: 15 }),
    [status, sourceId, debouncedQuery, page],
  );

  useEffect(() => {
    if (selectedId === null && list.data && list.data.items.length > 0) {
      setSelectedId(list.data.items[0].id);
    }
  }, [list.data, selectedId]);

  useEffect(() => {
    if (selectedId === null) {
      setDetail(null);
      return;
    }
    let alive = true;
    setDetailError('');
    getRaw(selectedId)
      .then((data) => {
        if (alive) setDetail(data);
      })
      .catch((err: Error) => {
        if (alive) setDetailError(err.message);
      });
    return () => {
      alive = false;
    };
  }, [selectedId]);

  const failedCount = counts.data?.find((item) => item.status === 'failed')?.count ?? 0;

  function refreshAll() {
    list.reload();
    counts.reload();
    if (selectedId !== null) {
      getRaw(selectedId).then(setDetail).catch(() => undefined);
    }
  }

  return (
    <div className="drawer-in">
      <SectionHead
        eyebrow="02 / RAW QUEUE"
        title="原始岗位队列 · raw ↔ 归一对照"
        aside={
          <>
            <span className="tag tag-rust">解析失败 {failedCount} 条</span>
            {detail ? <span className="tag">{detail.external_id}</span> : null}
          </>
        }
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '11.5rem minmax(0, 1.35fr) minmax(0, 1fr)',
          gap: '1rem',
          alignItems: 'start',
        }}
      >
        {/* 左：状态抽屉索引 */}
        <div className="card" style={{ padding: '0.5rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)', padding: '0.35rem 0.4rem' }}>
            解析状态
          </div>
          {STATUS_TABS.map((tab) => {
            const count = tab ? counts.data?.find((item) => item.status === tab)?.count ?? 0 : counts.data?.reduce((sum, item) => sum + item.count, 0) ?? 0;
            const active = status === tab;
            return (
              <button
                key={tab || 'all'}
                onClick={() => {
                  setStatus(tab);
                  setPage(1);
                  setSelectedId(null);
                }}
                data-testid={`raw-status-${tab || 'all'}`}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  width: '100%',
                  padding: '0.36rem 0.4rem',
                  marginBottom: 2,
                  border: 'none',
                  borderRadius: 2,
                  background: active ? 'var(--indigo)' : 'transparent',
                  color: active ? 'var(--paper-card)' : 'var(--ink)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--fs-small)',
                  textAlign: 'left',
                  cursor: 'pointer',
                }}
              >
                <span>{tab ? RAW_STATUS_LABELS[tab] : '全部'}</span>
                <span style={{ opacity: 0.75 }}>{count}</span>
              </button>
            );
          })}
          <div style={{ borderTop: '1px solid var(--paper-line)', margin: '0.5rem 0', padding: '0.5rem 0.4rem 0' }}>
            <select
              className="field"
              value={sourceId}
              onChange={(event) => {
                setSourceId(event.target.value ? Number(event.target.value) : '');
                setPage(1);
              }}
              style={{ width: '100%', border: '1px solid var(--paper-line)', background: 'var(--paper-card)', padding: '0.3rem', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)' }}
            >
              <option value="">全部采集源</option>
              {(sources.data || []).map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 中：队列表 */}
        <div>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.6rem' }}>
            <input
              className="field"
              data-testid="raw-search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setPage(1);
              }}
              placeholder="搜标题 / 薪资原文 / external_id"
              style={{ flex: 1, border: '1px solid var(--paper-line)', background: 'var(--paper-card)', padding: '0.42rem 0.55rem', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-small)' }}
            />
            <button className="btn btn-sm" onClick={refreshAll}>
              刷新
            </button>
          </div>
          {list.loading ? <LoadingBlock /> : null}
          {list.error ? <ErrorBlock message={list.error} onRetry={list.reload} /> : null}
          {!list.loading && !list.error && (list.data?.items.length || 0) === 0 ? (
            <EmptyState title="这个抽屉是空的" hint="换一个解析状态或清空搜索条件再试" />
          ) : null}
          {list.data && list.data.items.length > 0 ? (
            <div className="card" style={{ padding: '0.2rem 0.3rem' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>标题原文</th>
                    <th>薪资原文</th>
                    <th>城市</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.items.map((item) => (
                    <tr
                      key={item.id}
                      className={item.id === selectedId ? 'is-active' : ''}
                      onClick={() => setSelectedId(item.id)}
                      data-testid={`raw-row-${item.id}`}
                    >
                      <td className="mono" style={{ fontSize: 'var(--fs-micro)' }}>{item.id}</td>
                      <td>{item.title_raw}</td>
                      <td className="mono" style={{ color: 'var(--indigo)' }}>{item.salary_raw}</td>
                      <td>{item.city_raw.split('·')[0]}</td>
                      <td><StatusPill status={item.status} label={item.status_label} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          {list.data ? (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
              <span>
                共 {list.data.total} 条 · 第 {list.data.page}/{Math.max(list.data.pages, 1)} 页
              </span>
              <span style={{ display: 'flex', gap: '0.4rem' }}>
                <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
                <button className="btn btn-sm" disabled={page >= (list.data.pages || 1)} onClick={() => setPage((value) => value + 1)}>下一页</button>
              </span>
            </div>
          ) : null}
        </div>

        {/* 右：对照面板 */}
        <div className="card" style={{ padding: '1rem 1.1rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.14em', color: 'var(--copper)' }}>
            RAW → NORMALIZED
          </div>
          {detailError ? <ErrorBlock message={detailError} /> : null}
          {!detail && !detailError ? (
            <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--fs-small)' }}>点左侧任意一条原始岗位，查看解析前后的对照。</p>
          ) : null}
          {detail ? (
            <>
              <h3 style={{ fontSize: '1.05rem', margin: '0.35rem 0 0.15rem' }}>{detail.title_raw}</h3>
              <div style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)', marginBottom: '0.6rem' }} className="mono">
                {detail.source_name} · {detail.external_id} · {datetime(detail.published_at)}
              </div>
              <ParseDiffPanel detail={detail} />
              <div style={{ marginTop: '0.7rem', display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                {detail.current?.flags.map((flag) => (
                  <span key={flag} className="tag tag-rust">{QUALITY_LABELS[flag] || flag}</span>
                ))}
              </div>
              <CorrectionForm detail={detail} role={user?.role} onDone={(message) => { setNotice(message); refreshAll(); }} />
              {notice ? <p style={{ color: 'var(--sage)', fontSize: 'var(--fs-small)' }}>{notice}</p> : null}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function CorrectionForm({ detail, role, onDone }: { detail: RawDetail; role?: string; onDone: (message: string) => void }) {
  const [min, setMin] = useState('');
  const [max, setMax] = useState('');
  const [city, setCity] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const allowed = can(role, 'raw:correct');

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await correctRaw(detail.id, {
        salary_min: min ? Number(min) : undefined,
        salary_max: max ? Number(max) : undefined,
        city_raw: city || undefined,
      });
      onDone(`已修正 raw #${detail.id}，写入标准化岗位并标记 corrected`);
      setMin('');
      setMax('');
      setCity('');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ marginTop: '0.9rem', borderTop: '1px solid var(--paper-line)', paddingTop: '0.8rem' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)', marginBottom: '0.4rem' }}>
        人工修正（标注分析 / 数据主管）
      </div>
      <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
        <div className="field">
          <label>月薪下限</label>
          <input data-testid="correct-min" value={min} onChange={(event) => setMin(event.target.value)} placeholder="18000" style={{ width: '6.2rem' }} />
        </div>
        <div className="field">
          <label>月薪上限</label>
          <input data-testid="correct-max" value={max} onChange={(event) => setMax(event.target.value)} placeholder="22000" style={{ width: '6.2rem' }} />
        </div>
        <div className="field">
          <label>城市</label>
          <input value={city} onChange={(event) => setCity(event.target.value)} placeholder="杭州" style={{ width: '5rem' }} />
        </div>
        <button className="btn btn-sm btn-copper" data-testid="correct-submit" type="submit" disabled={!allowed || busy} style={{ alignSelf: 'flex-end' }}>
          {busy ? '提交中…' : '提交修正'}
        </button>
      </div>
      {!allowed ? <div style={{ marginTop: '0.35rem', fontSize: 'var(--fs-micro)', color: 'var(--rust)' }}>当前角色无修正权限（后端会返回 403）</div> : null}
      {error ? <div style={{ marginTop: '0.35rem', fontSize: 'var(--fs-small)', color: 'var(--rust)' }}>{error}</div> : null}
    </form>
  );
}
