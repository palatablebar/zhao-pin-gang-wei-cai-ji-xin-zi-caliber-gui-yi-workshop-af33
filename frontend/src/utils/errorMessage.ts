import { ApiError } from '../api/client';

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return `无权限：${error.message}`;
    if (error.status === 401) return '登录状态失效，请重新登录';
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return '未知错误';
}
