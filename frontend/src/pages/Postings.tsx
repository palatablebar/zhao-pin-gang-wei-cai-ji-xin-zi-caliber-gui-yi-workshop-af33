import { useEffect, useState } from 'react';
import { exportPostings, listPostings, postingStats } from '../api/postings';
import { useAsync } from '../hooks/useAsync';
import { usePostingFilters } from '../stores/filterStore';
import { useAuthStore } from '../stores/authStore';
import { can } from '../constants/roles';
import { CITIES, FUNCTION_LABELS, FUNCTION_TYPES, SENIORITIES, SENIORITY_LABELS } from '../constants/enums';
import { SectionHead } from '../components/common/SectionHead';
import { MetricCard } from '../components/common/MetricCard';
import { LoadingBlock } from '../components/common/LoadingBlock';
import { ErrorBlock } from '../components/common/ErrorBlock';
import { EmptyState } from '../components/common/EmptyState';
import { SalaryBandBar } from '../components/common/SalaryBandBar';
import { StatusPill } from '../components/common/StatusPill';
import { errorMessage } from '../utils/errorMessage';

export function PostingsPage() {
  const user = useAuthStore((state) => state.user);
  const filters = usePostingFilters();
  const [page, setPage] = useState(1);
  const [notice, setNotice] = useState('');

  const stats = useAsync(postingStats, []);
  const list = useAsync(
    () =>
      listPostings({
        city: filters.city || undefined,
        function_type: filters.functionType || undefined,
        seniority: filters.seniority || undefined,
        flagged: filters.flaggedOnly || undefined,
        page,
        size: 14,
      }),
    [filters.city, filters.functionType, filters.seniority, filters.flaggedOnly, page],
  );

  useEffect(() => {
    setPage(1);
  }, [filters.city, filters.functionType, filters.seniority, filters.flaggedOnly]);

  async function handleExport() {
    try {
      await exportPostings(filters.city || undefined, filters.functionType || undefined);
      setNotice('已导出 CSV（带 UTF-8 BOM，Excel 可直接打开）');
    } catch (err) {
      setNotice(errorMessage(err));
    }
  }

  return (
    <div className="drawer-in">
      <SectionHead
        eyebrow="03 / NORMALIZED POSTINGS"
        title="标准化结果表 · 月薪口径"
        aside={
          <>
            <span className="tag">{list.data?.total ?? 0} 条命中</span>
            <button className="btn btn-sm" data-testid="export-postings" onClick={handleExport} disabled={!can(user?.role, 'export')}>
              导出 CSV
            </button>
          </>
        }
      />

      <div className="grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', marginBottom: '0.9rem' }}>
        <MetricCard label="标准化岗位" value={stats.data?.total ?? '—'} hint="150 条目标本" />
        <MetricCard label="质量标记" value={stats.data?.flagged ?? '—'} hint="面议/日结/倒置/兼职/极端值" tone="copper" />
        <MetricCard label="人工修正" value={stats.data?.corrected ?? '—'} hint="修正后重跑不再覆盖" tone="indigo" />
        <MetricCard label="当前筛选" value={list.data?.total ?? '—'} hint={`${filters.city || '全部城市'} · ${filters.functionType ? FUNCTION_LABELS[filters.functionType] : '全部职能'}`} tone="sage" />
      </div>

      <div style={{ display: 'flex', gap: '0.7rem', flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: '0.8rem' }}>
        <div className="field">
          <label>城市</label>
          <select data-testid="filter-city" value={filters.city} onChange={(event) => filters.setFilter({ city: event.target.value })}>
            <option value="">全部</option>
            {CITIES.map((city) => (
              <option key={city} value={city}>{city}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>职能</label>
          <select data-testid="filter-function" value={filters.functionType} onChange={(event) => filters.setFilter({ functionType: event.target.value })}>
            <option value="">全部</option>
            {FUNCTION_TYPES.map((type) => (
              <option key={type} value={type}>{FUNCTION_LABELS[type]}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>职级</label>
          <select data-testid="filter-seniority" value={filters.seniority} onChange={(event) => filters.setFilter({ seniority: event.target.value })}>
            <option value="">全部</option>
            {SENIORITIES.map((level) => (
              <option key={level} value={level}>{SENIORITY_LABELS[level]}</option>
            ))}
          </select>
        </div>
        <label className="tag" style={{ cursor: 'pointer' }}>
          <input type="checkbox" checked={filters.flaggedOnly} onChange={(event) => filters.setFilter({ flaggedOnly: event.target.checked })} />
          只看质量标记
        </label>
        <button className="btn btn-sm btn-ghost" onClick={() => filters.reset()}>重置</button>
      </div>

      {notice ? <p style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>{notice}</p> : null}
      {list.loading ? <LoadingBlock /> : null}
      {list.error ? <ErrorBlock message={list.error} onRetry={list.reload} /> : null}
      {!list.loading && !list.error && (list.data?.items.length || 0) === 0 ? (
        <EmptyState title="该口径组合没有岗位" hint={`${filters.city || '全部城市'} / ${filters.functionType || '全部职能'} —— 换城市或职能试试`} />
      ) : null}

      {list.data && list.data.items.length > 0 ? (
        <div className="card" style={{ padding: '0.2rem 0.3rem' }}>
          <table className="table">
            <thead>
              <tr>
                <th>归一标题</th>
                <th>城市</th>
                <th>职能 / 职级</th>
                <th style={{ minWidth: 190 }}>月薪区间（刻度尺）</th>
                <th>口径</th>
                <th>质量</th>
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((posting) => (
                <tr key={posting.id} data-testid={`posting-row-${posting.id}`}>
                  <td>
                    <div style={{ fontWeight: 550 }}>{posting.canonical_title}</div>
                    <div className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
                      {posting.raw_title} · {posting.source_name}
                    </div>
                  </td>
                  <td>{posting.city}</td>
                  <td>
                    <span className="tag tag-indigo">{FUNCTION_LABELS[posting.function_type]}</span>{' '}
                    <span className="tag">{SENIORITY_LABELS[posting.seniority]}</span>
                  </td>
                  <td>
                    <SalaryBandBar
                      min={posting.salary_min}
                      max={posting.salary_max}
                      median={posting.salary_median}
                      annualMonths={posting.annual_months}
                      unit={posting.salary_unit}
                    />
                  </td>
                  <td className="mono" style={{ fontSize: 'var(--fs-micro)' }}>
                    {posting.salary_unit} · {posting.annual_months}薪
                    <br />
                    conf {posting.confidence.toFixed(2)}
                  </td>
                  <td>
                    {posting.quality_flags.length === 0 ? (
                      <StatusPill status="parsed" label="干净" />
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {posting.quality_flags.map((flag) => (
                          <StatusPill key={flag} status="needs_review" label={flag} />
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {list.data ? (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
          <span>共 {list.data.total} 条 · 第 {list.data.page}/{Math.max(list.data.pages, 1)} 页 · 区间条以 3K–60K 为刻度</span>
          <span style={{ display: 'flex', gap: '0.4rem' }}>
            <button className="btn btn-sm" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一页</button>
            <button className="btn btn-sm" disabled={page >= (list.data.pages || 1)} onClick={() => setPage((value) => value + 1)}>下一页</button>
          </span>
        </div>
      ) : null}
    </div>
  );
}
