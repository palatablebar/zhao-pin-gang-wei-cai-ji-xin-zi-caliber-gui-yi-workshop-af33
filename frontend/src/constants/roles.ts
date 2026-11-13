// 角色与权限（前端仅用于渲染入口；真实鉴权在后端中间件/依赖）。
export const ROLE_LABELS: Record<string, string> = {
  admin: '数据主管',
  analyst: '标注分析',
  client: 'HR 客户（只读）',
};

export const ROLE_DESCRIPTIONS: Record<string, string> = {
  admin: '口径规则版本、发布基准报表、采集源与审计',
  analyst: '修正标准化结果、重跑解析、处置质量队列，不能发布',
  client: '只读基准报表并导出 CSV，修正/发布一律 403',
};

// 与后端 PERMISSIONS 对齐的展示权限（后端是唯一事实源）
export const ROLE_PERMISSIONS: Record<string, string[]> = {
  admin: ['read', 'posting:correct', 'raw:correct', 'rule:trial', 'rule:reparse', 'rule:activate',
    'benchmark:generate', 'benchmark:publish', 'quality:dispose', 'source:sync', 'audit:read', 'export'],
  analyst: ['read', 'posting:correct', 'raw:correct', 'rule:trial', 'rule:reparse',
    'benchmark:generate', 'quality:dispose', 'export'],
  client: ['read', 'export'],
};

export function can(role: string | undefined, action: string): boolean {
  if (!role) return false;
  return (ROLE_PERMISSIONS[role] || []).includes(action);
}

export const NAV_ITEMS = [
  { path: '/sources', label: '采集源', code: '01', permission: 'read' },
  { path: '/raw', label: '原始队列', code: '02', permission: 'read' },
  { path: '/postings', label: '标准化表', code: '03', permission: 'read' },
  { path: '/rules', label: '口径规则', code: '04', permission: 'read' },
  { path: '/benchmarks', label: '基准报表', code: '05', permission: 'read' },
  { path: '/quality', label: '质量门禁', code: '06', permission: 'read' },
];
