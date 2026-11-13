// 共享枚举（前端副本）——与 backend/src/constants/enums.ts 保持一致。
// 出现位置：constants/enums.ts（定义）/ constants/roles.ts / pages/* / components/*
export const RAW_STATUSES = ['parsed', 'needs_review', 'failed', 'duplicate', 'invalid', 'corrected', 'quarantined'] as const;
export type RawStatus = (typeof RAW_STATUSES)[number];

export const RAW_STATUS_LABELS: Record<string, string> = {
  parsed: '已解析',
  needs_review: '待修正',
  failed: '解析失败',
  duplicate: '重复折叠',
  invalid: '脏原文',
  corrected: '人工修正',
  quarantined: '异常隔离',
};

export const FUNCTION_TYPES = ['backend', 'frontend', 'algorithm', 'test', 'devops', 'product', 'design', 'data'] as const;
export type FunctionType = (typeof FUNCTION_TYPES)[number];

export const FUNCTION_LABELS: Record<string, string> = {
  backend: '后端',
  frontend: '前端',
  algorithm: '算法',
  test: '测试',
  devops: '运维',
  product: '产品',
  design: '设计',
  data: '数据',
};

export const SENIORITIES = ['junior', 'mid', 'senior', 'staff', 'manager', 'director'] as const;
export type Seniority = (typeof SENIORITIES)[number];

export const SENIORITY_LABELS: Record<string, string> = {
  junior: '初级',
  mid: '中级',
  senior: '高级',
  staff: '资深',
  manager: '经理',
  director: '总监',
};

export const SALARY_UNITS = ['monthly', 'annual'] as const;
export const SALARY_UNIT_LABELS: Record<string, string> = { monthly: '月薪制', annual: '年薪制' };

export const QUALITY_FLAGS = ['negotiable', 'daily_wage', 'swapped', 'outlier', 'parttime', 'needs_review'] as const;
export const QUALITY_LABELS: Record<string, string> = {
  negotiable: '面议待补',
  daily_wage: '日结/时薪折算',
  swapped: '上下限倒置',
  outlier: '极端值',
  parttime: '兼职混入',
  needs_review: '待人工复核',
};

export const CITIES = ['杭州', '上海', '北京', '深圳', '广州', '成都', '武汉', '南京', '苏州', '西安'];

export const RULE_VERSIONS = ['v1', 'v2'] as const;

export const RULE_TYPE_LABELS: Record<string, string> = { salary: '薪资口径', title: '标题归一' };
