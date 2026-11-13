import { useState } from 'react';
import { activate, listRules, reparse, titleMerge, trial } from '../api/rules';
import { useAsync } from '../hooks/useAsync';
import { useAuthStore } from '../stores/authStore';
import { can } from '../constants/roles';
import type { ReparseResult, TrialResult } from '../types/models';
import { SectionHead } from '../components/common/SectionHead';
import { LoadingBlock } from '../components/common/LoadingBlock';
import { ErrorBlock } from '../components/common/ErrorBlock';
import { MetricCard } from '../components/common/MetricCard';
import { errorMessage } from '../utils/errorMessage';

const VERSIONS = ['v1', 'v2'];

export function RulesPage() {
  const user = useAuthStore((state) => state.user);
  const { data, loading, error, reload } = useAsync(listRules, []);
  const [trials, setTrials] = useState<Record<string, TrialResult>>({});
  const [reparseResult, setReparseResult] = useState<ReparseResult | null>(null);
  const [mergeInfo, setMergeInfo] = useState<string>('');
  const [busy, setBusy] = useState('');
  const [notice, setNotice] = useState('');
  const [err, setErr] = useState('');

  const rules = data || [];
  const activeVersion = rules.find((rule) => rule.is_active_set)?.version || 'v1';

  async function runTrial(version: string) {
    setBusy(`trial-${version}`);
    setErr('');
    try {
      const result = await trial(version);
      setTrials((prev) => ({ ...prev, [version]: result }));
    } catch (error_) {
      setErr(errorMessage(error_));
    } finally {
      setBusy('');
    }
  }

  async function runReparse(version: string) {
    setBusy(`reparse-${version}`);
    setErr('');
    setNotice('');
    try {
      const result = await reparse(version);
      setReparseResult(result);
      setNotice(`已按规则 ${version} 重跑 ${result.updated_raws} 条原始岗位，更新 ${result.updated_postings} 条标准化结果`);
      reload();
    } catch (error_) {
      setErr(errorMessage(error_));
    } finally {
      setBusy('');
    }
  }

  async function runActivate(version: string) {
    setBusy(`activate-${version}`);
    setErr('');
    try {
      await activate(version);
      setNotice(`规则版本 ${version} 已设为激活口径（admin）`);
      reload();
    } catch (error_) {
      setErr(errorMessage(error_));
    } finally {
      setBusy('');
    }
  }

  async function runMerge() {
    setBusy('merge');
    try {
      const result = await titleMerge();
      setMergeInfo(`3-gram Jaccard ≥ ${result.threshold} 归并演示：${result.merged_count} 条写法归入已有 canonical（${result.clusters.length} 个簇）`);
    } catch (error_) {
      setErr(errorMessage(error_));
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="drawer-in">
      <SectionHead
        eyebrow="04 / RULE VERSIONS"
        title="口径规则管理 · 版本化试跑"
        aside={
          <>
            <span className="tag tag-indigo">激活版本 {activeVersion}</span>
            <button className="btn btn-sm" data-testid="title-merge" onClick={runMerge} disabled={!can(user?.role, 'rule:trial') || busy === 'merge'}>
              标题 3-gram 归并演示
            </button>
          </>
        }
      />
      {loading ? <LoadingBlock /> : null}
      {error ? <ErrorBlock message={error} onRetry={reload} /> : null}
      {err ? <p style={{ color: 'var(--rust)', fontSize: 'var(--fs-small)' }}>{err}</p> : null}
      {notice ? <p style={{ color: 'var(--sage)', fontSize: 'var(--fs-small)' }}>{notice}</p> : null}
      {mergeInfo ? <p style={{ color: 'var(--ink-soft)', fontSize: 'var(--fs-small)' }}>{mergeInfo}</p> : null}

      {reparseResult ? (
        <div className="card drawer-in" style={{ padding: '1rem 1.2rem', marginBottom: '1rem', borderColor: 'var(--copper)' }} data-testid="reparse-result">
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.14em', color: 'var(--copper)' }}>
            REPARSE · {reparseResult.previous_version} → {reparseResult.active_version}
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '1.2rem', margin: '0.4rem 0' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '2.4rem', color: 'var(--indigo)' }}>
              {reparseResult.before.hit_rate_pct}% → {reparseResult.after.hit_rate_pct}%
            </div>
            <div style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
              命中 {reparseResult.before.hits}/{reparseResult.before.attempts} → {reparseResult.after.hits}/{reparseResult.after.attempts}
              <br />
              更新岗位 {reparseResult.updated_postings} 条 · 跳过人工修正 {reparseResult.skipped_corrected} 条 · 耗时 {reparseResult.duration_ms}ms
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            OK：{Object.entries(reparseResult.after.reason_breakdown).slice(0, 6).map(([reason, count]) => (
              <span key={reason} className="tag">{reason} × {count}</span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
        {VERSIONS.map((version) => {
          const versionRules = rules.filter((rule) => rule.version === version);
          const trialData = trials[version];
          return (
            <section key={version} className="card" style={{ padding: '1rem 1.15rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <h3 style={{ fontSize: '1.3rem' }}>
                  规则集 {version}
                  {version === 'v1' ? <span className="tag" style={{ marginLeft: '0.5rem' }}>历史基线</span> : null}
                  {version === 'v2' ? <span className="tag tag-copper" style={{ marginLeft: '0.5rem' }}>增补口径</span> : null}
                </h3>
                <span className="tag">{versionRules.length} 条规则</span>
              </div>
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', margin: '0.6rem 0' }}>
                <button className="btn btn-sm" data-testid={`trial-${version}`} onClick={() => runTrial(version)} disabled={!can(user?.role, 'rule:trial') || busy === `trial-${version}`}>
                  {busy === `trial-${version}` ? '试跑中…' : '试跑命中率'}
                </button>
                <button className="btn btn-sm btn-primary" data-testid={`reparse-${version}`} onClick={() => runReparse(version)} disabled={!can(user?.role, 'rule:reparse') || busy === `reparse-${version}`}>
                  {busy === `reparse-${version}` ? '重跑中…' : `切到 ${version} 重跑`}
                </button>
                <button
                  className="btn btn-sm btn-ghost"
                  data-testid={`activate-${version}`}
                  onClick={() => runActivate(version)}
                  disabled={!can(user?.role, 'rule:activate') || busy === `activate-${version}`}
                  title={can(user?.role, 'rule:activate') ? 'admin 才能激活版本' : '仅数据主管可激活'}
                >
                  激活版本
                </button>
              </div>

              {trialData ? (
                <div className="drawer-in" style={{ border: '1px solid var(--paper-line)', padding: '0.65rem 0.75rem', marginBottom: '0.6rem', background: 'var(--paper)' }}>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'baseline' }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.9rem', color: 'var(--indigo)' }}>{trialData.hit_rate_pct}%</div>
                    <div style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
                      命中 {trialData.hits} / {trialData.attempts}（{trialData.hit_rate}%）· 未命中 {trialData.misses}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginTop: '0.35rem' }}>
                    {Object.entries(trialData.reason_breakdown).map(([reason, count]) => (
                      <span key={reason} className="tag">{reason} × {count}</span>
                    ))}
                  </div>
                  <div style={{ marginTop: '0.4rem', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)', fontFamily: 'var(--font-mono)' }}>
                    {trialData.samples.slice(0, 4).map((sample) => (
                      <div key={sample.raw}>{sample.raw} → {sample.status} ({sample.reason_code})</div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                {versionRules.map((rule) => (
                  <div key={rule.id} style={{ borderTop: '1px dashed var(--paper-line)', paddingTop: '0.35rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                      <span style={{ fontSize: 'var(--fs-small)', fontWeight: 550 }}>{rule.name}</span>
                      <span className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>hit {rule.hit_count}</span>
                    </div>
                    <div className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--indigo)', wordBreak: 'break-all' }}>{rule.pattern}</div>
                    <div style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>{rule.description}</div>
                  </div>
                ))}
              </div>
            </section>
          );
        })}
      </div>

      <div className="card" style={{ marginTop: '1rem', padding: '0.9rem 1.1rem', fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
        口径口径：规则命中率 = 成功判定薪资语义（数值区间或明确面议）的条数 ÷ 尝试条数。
        v1 为历史基线（164/180 = 91.1%）；v2 增补面议识别、日结/时薪折算、中文千区间（173/180 = 96.1%）。
        试跑与重跑都由 Python `services/salary_parser.py` 真实计算并落库，前端不写死数值。
      </div>
    </div>
  );
}
