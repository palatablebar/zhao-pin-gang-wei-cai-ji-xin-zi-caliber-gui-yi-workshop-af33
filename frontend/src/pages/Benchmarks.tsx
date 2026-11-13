import { useEffect, useState } from 'react';
import { exportBenchmark, generate, getReport, listBenchmarks, publish } from '../api/benchmarks';
import { useAsync } from '../hooks/useAsync';
import { useAuthStore } from '../stores/authStore';
import { can } from '../constants/roles';
import { CITIES, FUNCTION_LABELS, FUNCTION_TYPES } from '../constants/enums';
import type { BenchmarkReport } from '../types/models';
import { SectionHead } from '../components/common/SectionHead';
import { MetricCard } from '../components/common/MetricCard';
import { SalaryBandBar } from '../components/common/SalaryBandBar';
import { LoadingBlock } from '../components/common/LoadingBlock';
import { ErrorBlock } from '../components/common/ErrorBlock';
import { EmptyState } from '../components/common/EmptyState';
import { StatusPill } from '../components/common/StatusPill';
import { kYuan } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';

export function BenchmarksPage() {
  const user = useAuthStore((state) => state.user);
  const list = useAsync(listBenchmarks, []);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [report, setReport] = useState<BenchmarkReport | null>(null);
  const [city, setCity] = useState('杭州');
  const [functionType, setFunctionType] = useState('backend');
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [err, setErr] = useState('');

  useEffect(() => {
    if (selectedId === null && list.data && list.data.length > 0) {
      const preferred = list.data.find((item) => item.city === '杭州' && item.function_type === 'backend') || list.data[0];
      setSelectedId(preferred.id);
    }
  }, [list.data, selectedId]);

  useEffect(() => {
    if (selectedId === null) {
      setReport(null);
      return;
    }
    let alive = true;
    getReport(selectedId)
      .then((data) => {
        if (alive) setReport(data);
      })
      .catch((error_) => {
        if (alive) setErr(errorMessage(error_));
      });
    return () => {
      alive = false;
    };
  }, [selectedId]);

  async function handleGenerate() {
    setBusy('generate');
    setErr('');
    setNotice('');
    try {
      const result = await generate(city, functionType);
      setNotice(`已生成 ${result.city}/${FUNCTION_LABELS[result.function_type]} 基准 v${result.version}（样本 ${result.sample_count}）`);
      const fresh = await getReport(result.id);
      setReport(fresh);
      list.reload();
      setSelectedId(result.id);
    } catch (error_) {
      setErr(errorMessage(error_));
    } finally {
      setBusy('');
    }
  }

  async function handlePublish() {
    if (!selectedId) return;
    setBusy('publish');
    try {
      await publish(selectedId);
      setNotice('基准报表已发布（admin）');
      const fresh = await getReport(selectedId);
      setReport(fresh);
      list.reload();
    } catch (error_) {
      setErr(errorMessage(error_));
    } finally {
      setBusy('');
    }
  }

  async function handleExport() {
    if (!selectedId) return;
    try {
      await exportBenchmark(selectedId);
      setNotice('基准 CSV 已导出');
    } catch (error_) {
      setErr(errorMessage(error_));
    }
  }

  const benchmarks = list.data || [];
  const floor = 5000;
  const ceiling = report ? Math.max(report.p75 * 1.25, report.p50 * 2) : 60000;

  return (
    <div className="drawer-in">
      <SectionHead
        eyebrow="05 / SALARY BENCHMARKS"
        title="薪资基准报表 · P25 / P50 / P75"
        aside={
          <>
            <span className="tag">当前：{report ? `${report.city} · ${FUNCTION_LABELS[report.function_type]}` : '—'}</span>
            <button className="btn btn-sm" data-testid="export-benchmark" onClick={handleExport} disabled={!selectedId || !can(user?.role, 'export')}>
              导出 CSV
            </button>
            <button className="btn btn-sm btn-copper" data-testid="publish-benchmark" onClick={handlePublish} disabled={!selectedId || !can(user?.role, 'benchmark:publish') || busy === 'publish'}>
              发布基准
            </button>
          </>
        }
      />

      {list.loading ? <LoadingBlock /> : null}
      {list.error ? <ErrorBlock message={list.error} onRetry={list.reload} /> : null}
      {err ? <p style={{ color: 'var(--rust)', fontSize: 'var(--fs-small)' }}>{err}</p> : null}
      {notice ? <p style={{ color: 'var(--sage)', fontSize: 'var(--fs-small)' }}>{notice}</p> : null}

      <div style={{ display: 'grid', gridTemplateColumns: '17rem minmax(0, 1fr)', gap: '1.1rem', alignItems: 'start' }}>
        <div>
          <div className="card" style={{ padding: '0.8rem', marginBottom: '0.8rem' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--copper)', marginBottom: '0.45rem' }}>
              生成基准报表
            </div>
            <div className="field" style={{ marginBottom: '0.45rem' }}>
              <label>城市</label>
              <select data-testid="benchmark-city" value={city} onChange={(event) => setCity(event.target.value)}>
                {CITIES.slice(0, 5).map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
            </div>
            <div className="field" style={{ marginBottom: '0.55rem' }}>
              <label>职能</label>
              <select data-testid="benchmark-function" value={functionType} onChange={(event) => setFunctionType(event.target.value)}>
                {FUNCTION_TYPES.map((item) => (
                  <option key={item} value={item}>{FUNCTION_LABELS[item]}</option>
                ))}
              </select>
            </div>
            <button className="btn btn-sm btn-primary" data-testid="generate-benchmark" style={{ width: '100%' }} onClick={handleGenerate} disabled={!can(user?.role, 'benchmark:generate') || busy === 'generate'}>
              {busy === 'generate' ? '计算中…' : '生成 / 重算基准'}
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
            {benchmarks.map((item) => (
              <button
                key={item.id}
                onClick={() => setSelectedId(item.id)}
                data-testid={`benchmark-item-${item.id}`}
                className="card card-hover"
                style={{
                  textAlign: 'left',
                  padding: '0.65rem 0.8rem',
                  borderLeft: item.id === selectedId ? '3px solid var(--copper)' : '1px solid var(--paper-line)',
                  cursor: 'pointer',
                  background: 'var(--paper-card)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <span style={{ fontWeight: 560 }}>{item.city} · {FUNCTION_LABELS[item.function_type]}</span>
                  <StatusPill status={item.published ? 'published' : 'draft'} label={item.published ? '已发布' : '草稿'} />
                </div>
                <div className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
                  样本 {item.sample_count} · P50 {kYuan(item.p50)} · v{item.version}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div>
          {!report ? (
            <EmptyState title="还没有选中报表" hint="左侧选择一份基准，或先生成杭州 / backend 基准" />
          ) : (
            <div className="card drawer-in" style={{ padding: '1.1rem 1.25rem' }} data-testid="benchmark-report">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.14em', color: 'var(--copper)' }}>
                    {report.city} / {report.function_type} · 规则 {report.rule_version} · v{report.version}
                  </div>
                  <h2 style={{ fontSize: '1.6rem', margin: '0.15rem 0' }}>
                    {report.city} {FUNCTION_LABELS[report.function_type]} 薪资基准
                  </h2>
                  <div style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
                    样本 {report.sample_count} 条（已排除质量标记与面议） · {report.published ? '已发布' : '草稿，待 admin 发布'}
                  </div>
                </div>
                <StatusPill status={report.published ? 'published' : 'draft'} label={report.published ? 'PUBLISHED' : 'DRAFT'} />
              </div>

              <div className="grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', margin: '0.9rem 0' }}>
                <MetricCard label="P25 · 下四分位" value={kYuan(report.p25)} hint="¥ 月薪" tone="sage" />
                <MetricCard label="P50 · 中位数" value={kYuan(report.p50)} hint="¥ 月薪" tone="indigo" />
                <MetricCard label="P75 · 上四分位" value={kYuan(report.p75)} hint="¥ 月薪" tone="copper" />
              </div>

              <div style={{ margin: '0.8rem 0 1rem' }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)', marginBottom: '0.3rem' }}>
                  P25–P75 薪资区间（细线刻度尺）
                </div>
                <SalaryBandBar
                  min={report.p25}
                  max={report.p75}
                  median={report.p50}
                  annualMonths={12}
                  explicitFloor={floor}
                  explicitCeiling={ceiling}
                  height={38}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '1rem' }}>
                <div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)', marginBottom: '0.35rem' }}>
                    样本分布（月薪中位数 · 直方桶）
                  </div>
                  {report.distribution.map((bucket) => {
                    const maxCount = Math.max(...report.distribution.map((item) => item.count), 1);
                    return (
                      <div key={`${bucket.low}-${bucket.high}`} style={{ display: 'grid', gridTemplateColumns: '5.4rem 1fr 1.6rem', gap: '0.4rem', alignItems: 'center', marginBottom: 3 }}>
                        <span className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>{kYuan(bucket.low)}–{kYuan(bucket.high)}</span>
                        <div style={{ height: 9, background: 'oklch(92% 0.02 82)' }}>
                          <div style={{ width: `${(bucket.count / maxCount) * 100}%`, height: '100%', background: 'var(--indigo)' }} />
                        </div>
                        <span className="mono" style={{ fontSize: 'var(--fs-micro)' }}>{bucket.count}</span>
                      </div>
                    );
                  })}
                </div>
                <div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', color: 'var(--ink-soft)', marginBottom: '0.35rem' }}>
                    职级拆分 · n / P50
                  </div>
                  <table className="table">
                    <thead>
                      <tr><th>职级</th><th>样本</th><th>P50</th></tr>
                    </thead>
                    <tbody>
                      {report.seniority_breakdown.map((row) => (
                        <tr key={row.seniority} style={{ cursor: 'default' }}>
                          <td>{row.label}</td>
                          <td className="mono">{row.sample_count}</td>
                          <td className="mono">{kYuan(row.p50)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
