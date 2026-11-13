import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { NAV_ITEMS, ROLE_LABELS } from '../../constants/roles';
import { useAuthStore } from '../../stores/authStore';

export function AppShell() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();

  const items = user?.role === 'client' ? NAV_ITEMS.filter((item) => item.path === '/benchmarks') : NAV_ITEMS;

  return (
    <div
      className="app-shell"
      style={{
        display: 'grid',
        gridTemplateColumns: '15.5rem 1fr',
        minHeight: '100vh',
        maxWidth: 1680,
        margin: '0 auto',
      }}
    >
      {/* 左侧抽屉索引列 */}
      <aside
        style={{
          borderRight: '1px solid var(--paper-line)',
          background:
            'linear-gradient(180deg, oklch(94% 0.026 82) 0%, oklch(90.5% 0.03 80) 100%)',
          padding: '1.4rem 1rem 1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.2rem',
        }}
      >
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', letterSpacing: '0.22em', color: 'var(--copper)' }}>
            GANGXIAN DATA · 岗线数据
          </div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.9rem', lineHeight: 1.02, marginTop: '0.3rem', letterSpacing: '-0.01em' }}>
            jobnorm
          </div>
          <div style={{ fontSize: 'var(--fs-small)', color: 'var(--ink-soft)', marginTop: '0.2rem' }}>
            招聘岗位 · 薪资口径归一
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--paper-line)' }} />

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
          {items.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'grid',
                gridTemplateColumns: '2.1rem 1fr',
                alignItems: 'baseline',
                gap: '0.4rem',
                padding: '0.5rem 0.55rem',
                textDecoration: 'none',
                color: isActive ? 'var(--paper-card)' : 'var(--ink)',
                background: isActive ? 'var(--indigo)' : 'transparent',
                border: '1px solid',
                borderColor: isActive ? 'var(--indigo-deep)' : 'transparent',
                borderRadius: 2,
                transition: 'all 200ms var(--ease-out)',
              })}
            >
              {({ isActive }) => (
                <>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-micro)', opacity: 0.75 }}>
                    {item.code}
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-small)', letterSpacing: '0.04em' }}>
                    {item.label}
                    {isActive ? ' ▸' : ''}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div style={{ marginTop: 'auto', fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)', lineHeight: 1.5 }}>
          <div style={{ borderTop: '1px solid var(--paper-line)', paddingTop: '0.8rem' }}>
            卡片目录柜 v1.0
            <br />
            5 源 · 180 原始 · 150 标准化
          </div>
        </div>

        <div style={{ borderTop: '1px solid var(--paper-line)', paddingTop: '0.7rem' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-small)' }}>{user?.name}</div>
          <div style={{ fontSize: 'var(--fs-micro)', color: 'var(--ink-soft)' }}>
            {ROLE_LABELS[user?.role || ''] || user?.role}
          </div>
          <button
            className="btn btn-sm"
            style={{ marginTop: '0.55rem', width: '100%' }}
            onClick={() => {
              logout();
              navigate('/login');
            }}
          >
            退出登录
          </button>
        </div>
      </aside>

      <main style={{ padding: '1.5rem 1.8rem 3rem', minWidth: 0 }}>
        <Outlet />
      </main>
    </div>
  );
}
