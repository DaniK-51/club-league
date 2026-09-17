import { create } from 'zustand'
import type { MeResponse } from '@/lib/api-client'

interface AuthState {
  user: MeResponse | null
  accessToken: string | null
  setAuth: (user: MeResponse, accessToken: string) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  setAuth: (user, accessToken) => set({ user, accessToken }),
  clear: () => set({ user: null, accessToken: null }),
}))
