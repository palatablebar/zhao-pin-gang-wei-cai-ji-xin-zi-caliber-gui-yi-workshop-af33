import { useEffect, useState } from 'react';
import { dispose, listQuality } from '../api/quality';
import { getRaw } from '../api/raw';
import { useAsync } from '../hooks/useAsync';
import { useAuthStore } from '../stores/authStore';
import { can } from '../constants/roles';
import type { QualityItem, RawDetail } from '../types/models';
import { SectionHead } from '../components/common/SectionHead';
import { ParseDiffPanel } from '../components/common/ParseDiffPanel';
import { LoadingBlock } from '../components/common/LoadingBlock';
import { ErrorBlock } from '../components/common/ErrorBlock';
import { EmptyState } from '../components/common/EmptyState';
import { StatusPill } from '../components/common/StatusPill';
import { QUALITY_LABELS } from '../constants/enums';
import { kYuan } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';

export function QualityPage() {
  const user = useAuthStore((state) => state.user);
  const [flag, setFlag] = useState('');
  const [status, setStatus] = useState('');
  const [selected, setSelected] = useState<QualityItem | null>(null);
  const [rawDetail, setRawDetail] = useState<RawDetail | null>(null);
  const [note, setNote] = useState('');
  const [action, setAction] = useState<'disposed' | 'ignored'>('disposed');
  const [notice, setNotice] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const list = useAsync(() => listQuality({ flag: flag || undefined, status: status || undefined, size: 30 }), [flag, status]);
  const items = list.data?.items || [];

  useEffect(() => {
    if (selected === null && items.length > 0) setSelected(items[0]);
  }, [items, selected]);

  useEffect(() => {
    if (!selected) {
      setRawDetail(null);
      return;
    }
    let alive = true;
    getRaw(selected.posting.raw_id)
      .then((data) => {
        if (alive) setRawDetail(data);
      })
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [selected]);

  async function handleDispose() {
    if (!selected) return;
    setBusy(true);
    setErr('');
    try {
      const result = await dispose(selected.posting.id, action, note || '人工复核通过');
      setNotice(`posting #${result.posting_id} 已处置为 ${result.quality_status}`);
      setNote('');
      list.reload();
    } catch (error_) {
      setErr(errorMessage(error_));
    } finally {
      setBusy(false);
    }
  }

  const byType = list.data?.by_type || [];

  return (
    <div className="drawer-in">
      <SectionHead
        eyebrow="06 / QUALITY GATE"
        title="质量门禁队列 · 异常分类处置"
        aside={
          <>
            <span className="tag tag-copper">待处置 {list.data?.total ?? 0} 条</span>
            <select
              className="field"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              style={{ border: '1px solid var(--paper-line)', padding: '0.25rem 0.4rem', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)' }}
            >
              <option value="">全部状态</option>
              <option value="open">待处置</option>
              <option value="disposed">已处置</option>
              <option value="ignored">已忽略</option>
            </select>
          </>
        }
      />

      <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '0.8rem' }}>
        <button className={`btn btn-sm ${flag === '' ? 'btn-primary' : ''}`} onClick={() => setFlag('')} data-testid="quality-flag-all">
          全部类型
        </button>
        {byType.map((item) => (
          <button
            key={item.flag}
            className={`btn btn-sm ${flag === item.flag ? 'btn-primary' : ''}`}
            onClick={() => setFlag(item.flag)}
            data-testid={`quality-flag-${item.flag}`}
          >
            {QUALITY_LABELS[item.flag] || item.flag} × {item.count}
          </button>
        ))}
      </div>

      {list.loading ? <LoadingBlock /> : null}
      {list.error ? <ErrorBlock message={list.error} onRetry={list.reload} /> : null}
      {err ? <p style={{ color: 'var(--rust)', fontSize: 'var(--fs-small)' }}>{err}</p> : null}
      {notice ? <p style={{ color: 'var(--sage)', fontSize: 'var(--fs-small)' }}>{notice}</p> : null}

      {!list.loading && !list.error && items.length === 0 ? (
        <EmptyState title="队列已清空" hint="该类型下没有待处置条目，可以切回全部类型" />
      ) : null}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(0, 1fr)', gap: '1rem', alignItems: 'start' }}>
        <div className="card" style={{ padding: '0.2rem 0.3rem' }}>
          <table className="table">
            <thead>
              <tr>
                <th>岗位</th>
                <th>城市 / 职能</th>
                <th>异常类型</th>
                <th>月薪</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.posting.id}
                  className={selected?.posting.id === item.posting.id ? 'is-active' : ''}
                  onClick={() => setSelected(item)}
                  data-testid={`quality-row-${item.posting.id}`}
                >
                  <td>
                    <div style={{ fontWeight: 550 }}>{item.posting.canonical_title}</div>
                    <div className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>{item.posting.raw_title}</div>
                  </td>
                  <td>
                    {item.posting.city} · {item.posting.function_label}
                  </td>
                  <td>
                    <span className="tag tag-rust">{item.flag_labels[0] || item.primary_flag}</span>
                  </td>
                  <td className="mono" style={{ fontSize: 'var(--fs-small)' }}>
                    {item.posting.salary_median === null ? '待补' : kYuan(item.posting.salary_median)}
                  </td>
                  <td><StatusPill status={item.posting.quality_status} label={item.posting.quality_status === 'open' ? '待处置' : item.posting.quality_status === 'disposed' ? '已处置' : '已忽略'} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card" style={{ padding: '1rem 1.1rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.14em', color: 'var(--copper)' }}>
            QUALITY REVIEW
          </div>
          {!selected ? (
            <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--fs-small)' }}>左侧选择一条待处置异常。</p>
          ) : (
            <>
              <h3 style={{ fontSize: '1.05rem', margin: '0.3rem 0 0.15rem' }}>{selected.posting.canonical_title}</h3>
              <div className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)', marginBottom: '0.6rem' }}>
                {selected.posting.source_name} · 原始薪资 {selected.posting.raw_salary}
              </div>
              <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
                {selected.posting.quality_flags.map((item) => (
                  <span key={item} className="tag tag-rust">{QUALITY_LABELS[item] || item}</span>
                ))}
                <span className="tag">规则 {selected.posting.rule_version}</span>
              </div>
              {rawDetail ? <ParseDiffPanel detail={rawDetail} compact /> : <LoadingBlock label="读取原文…" />}
              <div style={{ borderTop: '1px solid var(--paper-line)', marginTop: '0.8rem', paddingTop: '0.7rem' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)', marginBottom: '0.4rem' }}>
                  处置（标注分析 / 数据主管）
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                  <div className="field">
                    <label>处置动作</label>
                    <select value={action} onChange={(event) => setAction(event.target.value as 'disposed' | 'ignored')}>
                      <option value="disposed">确认修复（disposed）</option>
                      <option value="ignored">标记忽略（ignored）</option>
                    </select>
                  </div>
                  <div className="field" style={{ flex: 1, minWidth: '9rem' }}>
                    <label>处置备注</label>
                    <input data-testid="dispose-note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="例：按 22 工作日折算确认" />
                  </div>
                  <button className="btn btn-sm btn-copper" data-testid="dispose-submit" onClick={handleDispose} disabled={!can(user?.role, 'quality:dispose') || busy}>
                    {busy ? '提交中…' : '提交处置'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: '1rem', padding: '0.9rem 1.1rem', fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
        异常来源：面议 4 条（薪资 null，需补录或确认可比口径）、日结/时薪 3 条（已折算月薪，标记待复核）、
        上下限倒置 2 条（自动交换并标 swapped）、兼职混入 2 条（is_fulltime=false）、极端值 1 条（1200K 越界）。
        共 12 条，全部由 Python 解析器的校验分支产出。
      </div>
    </div>
  );
}
