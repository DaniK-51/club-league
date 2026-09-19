import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { useAuthStore } from '@/store/auth.store'

export function useSsoCallback() {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation({
    mutationFn: (code: string) => api.ssoCallback(code),
    onSuccess: (data) => {
      setAuth(data.user, data.accessToken, data.refreshToken)
    },
  })
}

export function useMe(enabled = true) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  return useQuery({
    queryKey: ['me'],
    queryFn: () => api.getMe(),
    enabled: enabled && isAuthenticated,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLogout() {
  const clear = useAuthStore((s) => s.clear)
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async () => {
      clear()
    },
    onSuccess: () => {
      queryClient.clear()
    },
  })
}
