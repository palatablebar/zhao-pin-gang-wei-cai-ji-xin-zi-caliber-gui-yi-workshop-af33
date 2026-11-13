import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/auth';
import { useAuthStore } from '../stores/authStore';
import { ROLE_DESCRIPTIONS, ROLE_LABELS } from '../constants/roles';
import { errorMessage } from '../utils/errorMessage';

const DEMO_ACCOUNTS = [
  { email: 'admin@jobnorm.io', role: 'admin' },
  { email: 'analyst@jobnorm.io', role: 'analyst' },
  { email: 'client@jobnorm.io', role: 'client' },
];

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [email, setEmail] = useState('analyst@jobnorm.io');
  const [password, setPassword] = useState('Demo@2026');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const result = await login(email, password);
      setSession(result.access_token, result.user);
      navigate(result.user.role === 'client' ? '/benchmarks' : '/sources');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        gridTemplateColumns: '1.15fr 0.85fr',
        maxWidth: 1560,
        margin: '0 auto',
      }}
    >
      <section style={{ padding: 'clamp(2rem, 5vw, 5rem)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.24em', color: 'var(--copper)' }}>
          GANGXIAN DATA · JOB SALARY NORMALIZATION WORKSHOP
        </div>
        <div>
          <h1 style={{ fontSize: 'clamp(2.4rem, 4.4vw, 4.2rem)', lineHeight: 1.03, letterSpacing: '-0.02em' }}>
            把「15-25K·14薪」<br />
            变成同一把尺子
          </h1>
          <p style={{ maxWidth: 560, fontSize: '1.02rem', lineHeight: 1.7, color: 'var(--ink-soft)' }}>
            岗线数据为 30 家 HR 客户提供岗位画像与薪资基准。五个招聘源的薪资文本口径混杂
            —— 年薪、月薪、日结、13~16 薪 —— 我们把它归一成可比的月薪口径，再做职级职能映射与质量门禁。
          </p>
          <div style={{ display: 'flex', gap: '2.2rem', marginTop: '1.4rem', flexWrap: 'wrap' }}>
            {[
              ['180', '原始岗位 / 5 源'],
              ['150', '标准化岗位'],
              ['12', '质量门禁条目'],
              ['3', '城市基准报表'],
            ].map(([value, label]) => (
              <div key={label}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.8rem', color: 'var(--indigo)' }}>{value}</div>
                <div style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)', letterSpacing: '0.1em' }}>
          卡片目录柜 · 档案抽屉 · 口径版本 v1 / v2 · DEMO 环境
        </div>
      </section>

      <section
        style={{
          borderLeft: '1px solid var(--paper-line)',
          background: 'linear-gradient(180deg, oklch(95% 0.024 84), oklch(91% 0.03 80))',
          padding: 'clamp(1.6rem, 4vw, 3.4rem)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: '1.2rem',
        }}
      >
        <div className="card drawer-in" style={{ padding: '1.6rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.16em', color: 'var(--copper)' }}>
            档案调阅 · SIGN IN
          </div>
          <h2 style={{ fontSize: 'var(--fs-title)', margin: '0.3rem 0 1.1rem' }}>登录归一口径工作台</h2>
          <form onSubmit={submit} style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
            <div className="field">
              <label htmlFor="email">邮箱</label>
              <input
                id="email"
                data-testid="login-email"
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="password">密码</label>
              <input
                id="password"
                data-testid="login-password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
            {error ? <div style={{ color: 'var(--rust)', fontSize: 'var(--fs-small)' }}>{error}</div> : null}
            <button className="btn btn-primary" data-testid="login-submit" type="submit" disabled={busy}>
              {busy ? '核验中…' : '进入工坊'}
            </button>
          </form>
        </div>

        <div style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.12em', marginBottom: '0.4rem' }}>
            演示账号 · 密码统一 Demo@2026
          </div>
          {DEMO_ACCOUNTS.map((account) => (
            <div key={account.email} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.6rem', padding: '0.2rem 0' }}>
              <button
                className="btn btn-sm"
                style={{ border: 'none', padding: 0, background: 'transparent', color: 'var(--indigo)', textAlign: 'left' }}
                onClick={() => setEmail(account.email)}
                type="button"
              >
                {account.email}
              </button>
              <span className="mono" style={{ fontSize: 'var(--fs-micro)' }}>{ROLE_LABELS[account.role]}</span>
            </div>
          ))}
          <div style={{ marginTop: '0.5rem', fontSize: 'var(--fs-micro)' }}>
            {ROLE_DESCRIPTIONS.client}
          </div>
        </div>
      </section>
    </div>
  );
}
