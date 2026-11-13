import { create } from 'zustand';

export interface PostingFilterState {
  city: string;
  functionType: string;
  seniority: string;
  flaggedOnly: boolean;
  setFilter: (patch: Partial<Omit<PostingFilterState, 'setFilter'>>) => void;
  reset: () => void;
}

const initial = { city: '', functionType: '', seniority: '', flaggedOnly: false };

export const usePostingFilters = create<PostingFilterState>((set) => ({
  ...initial,
  setFilter: (patch) => set(patch),
  reset: () => set(initial),
}));
