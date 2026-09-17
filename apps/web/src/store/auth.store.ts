import { create } from 'zustand'
import type { MeResponse } from '@/lib/types'
import { api } from '@/lib/api-client'

const STORAGE_KEY = 'club-league-auth'

interface PersistedAuth {
  accessToken: string
  refreshToken: string
  user: MeResponse
}

function loadPersisted(): PersistedAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw) as PersistedAuth
  } catch {
    return null
  }
}

function persist(data: PersistedAuth | null) {
  if (data) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

interface AuthState {
  user: MeResponse | null
  isAuthenticated: boolean
  setAuth: (user: MeResponse, accessToken: string, refreshToken: string) => void
  clear: () => void
  init: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,

  setAuth: (user, accessToken, refreshToken) => {
    api.setTokens(accessToken, refreshToken)
    persist({ accessToken, refreshToken, user })
    set({ user, isAuthenticated: true })
  },

  clear: () => {
    api.setTokens(null, null)
    persist(null)
    set({ user: null, isAuthenticated: false })
  },

  init: () => {
    const saved = loadPersisted()
    if (saved) {
      api.setTokens(saved.accessToken, saved.refreshToken)
      set({ user: saved.user, isAuthenticated: true })
    }
  },
}))

// Sync store when API client refreshes tokens
api.setOnTokenChange((accessToken) => {
  if (!accessToken) {
    useAuthStore.getState().clear()
  }
})
