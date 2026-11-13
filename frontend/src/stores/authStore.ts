import { create } from 'zustand';
import type { User } from '../types/models';
import { setToken } from '../api/client';

interface AuthState {
  token: string | null;
  user: User | null;
  setSession: (token: string, user: User) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

function readUser(): User | null {
  try {
    const raw = localStorage.getItem('jobnorm.user');
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('jobnorm.token'),
  user: readUser(),
  setSession: (token, user) => {
    setToken(token);
    localStorage.setItem('jobnorm.user', JSON.stringify(user));
    set({ token, user });
  },
  setUser: (user) => {
    localStorage.setItem('jobnorm.user', JSON.stringify(user));
    set({ user });
  },
  logout: () => {
    setToken(null);
    localStorage.removeItem('jobnorm.user');
    set({ token: null, user: null });
  },
}));
