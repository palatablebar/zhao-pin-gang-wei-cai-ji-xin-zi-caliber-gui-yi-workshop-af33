import { request } from './client';
import type { LoginResponse, User } from '../types/models';

export function login(email: string, password: string): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/login', { method: 'POST', body: { email, password } });
}

export function me(): Promise<User> {
  return request<User>('/auth/me');
}

export function listUsers(): Promise<User[]> {
  return request<User[]>('/auth/users');
}
