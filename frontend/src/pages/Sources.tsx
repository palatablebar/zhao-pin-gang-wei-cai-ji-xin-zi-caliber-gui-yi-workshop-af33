import { useState } from 'react';
import { listSources, syncSource } from '../api/sources';
import { useAsync } from '../hooks/useAsync';
import { useAuthStore } from '../stores/authStore';
import { can } from '../constants/roles';
import { SectionHead } from '../components/common/SectionHead';
import { MetricCard } from '../components/common/MetricCard';
import { StatusPill } from '../components/common/StatusPill';
import { LoadingBlock } from '../components/common/LoadingBlock';
import { ErrorBlock } from '../components/common/ErrorBlock';
import { EmptyState } from '../components/common/EmptyState';
import { datetime } from '../utils/format';
import { errorMessage } from '../utils/errorMessage';

export function SourcesPage() {
  const user = useAuthStore((state) => state.user);
  const { data, loading, error, reload } = useAsync(listSources, []);
  const [notice, setNotice] = useState('');
  const [syncError, setSyncError] = useState('');
  const [syncing, setSyncing] = useState<number | null>(null);

  async function handleSync(id: number) {
    setSyncing(id);
    setSyncError('');
    setNotice('');
    try {
      const result = await syncSource(id);
      setNotice(`已投递后台同步任务 ${result.task_id.slice(0, 8)}…（Celery worker 消费）`);
      window.setTimeout(reload, 2200);
    } catch (err) {
      setSyncError(errorMessage(err));
    } finally {
      setSyncing(null);
    }
  }

  const sources = data || [];
  const totalRaw = sources.reduce((sum, source) => sum + source.raw_count, 0);

  return (
    <div className="drawer-in">
      <SectionHead
        eyebrow="01 / SOURCES"
        title="采集源与同步状态"
        aside={<span className="tag">{sources.filter((s) => s.enabled).length} / {sources.length} 启用</span>}
      />
      {loading ? <LoadingBlock /> : null}
      {error ? <ErrorBlock message={error} onRetry={reload} /> : null}
      {!loading && !error && sources.length === 0 ? <EmptyState title="还没有采集源" hint="运行 seed 后会载入 5 个演示源" /> : null}

      <div className="grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', marginBottom: '1rem' }}>
        <MetricCard label="采集源" value={sources.length} hint="招聘网站 / 企业官网 / 猎头" />
        <MetricCard label="原始岗位" value={totalRaw} hint="跨源采集总量（含重复折叠）" tone="copper" />
        <MetricCard label="启用中" value={sources.filter((s) => s.enabled).length} hint="停用源不参与调度" tone="sage" />
      </div>

      {notice ? <p style={{ color: 'var(--sage)', fontSize: 'var(--fs-small)' }}>{notice}</p> : null}
      {syncError ? <p style={{ color: 'var(--rust)', fontSize: 'var(--fs-small)' }}>{syncError}</p> : null}

      <div className="grid" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
        {sources.map((source) => (
          <article key={source.id} className="card card-hover" style={{ padding: '1rem 1.1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.6rem', alignItems: 'baseline' }}>
              <h3 style={{ fontSize: '1.12rem' }}>{source.name}</h3>
              <StatusPill status={source.sync_status} label={source.sync_status === 'idle' ? '就绪' : source.sync_status} />
            </div>
            <div style={{ display: 'flex', gap: '0.4rem', margin: '0.45rem 0', flexWrap: 'wrap' }}>
              <span className="tag tag-indigo">{source.site_type_label}</span>
              <span className="tag">{source.raw_count} 条原始</span>
              <span className="tag">{source.enabled ? '已启用' : '已停用'}</span>
            </div>
            <p style={{ margin: '0.2rem 0', fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>{source.note}</p>
            <div className="mono" style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)', marginBottom: '0.7rem' }}>
              最近同步：{datetime(source.last_sync_at)}
            </div>
            <button
              className="btn btn-sm"
              disabled={!can(user?.role, 'source:sync') || syncing === source.id}
              onClick={() => handleSync(source.id)}
              title={can(user?.role, 'source:sync') ? '投递 Celery 模拟同步任务' : '仅数据主管可触发同步'}
            >
              {syncing === source.id ? '投递中…' : '模拟同步 2 条'}
            </button>
          </article>
        ))}
      </div>

      <div className="card" style={{ marginTop: '1.2rem', padding: '0.9rem 1.1rem', fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
        本演示不真发爬取请求：seed 的原始 JSON 代表已采集入湖数据，「模拟同步」由 Celery worker
        异步投递到采集入库（同一公司+城市+职位只保留最新薪酬，external_id 幂等，重复点击不新增岗位）。
        多来源重送、迟到旧版本与异常隔离见「采集入库」页。
      </div>
    </div>
  );
}
