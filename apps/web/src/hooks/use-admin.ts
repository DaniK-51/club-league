import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { UpdateRuleDTO } from '@/lib/types'

// === Hooks ===

export function useAuditLog(
  entityType?: string,
  entityId?: string,
  limit = 50,
  offset = 0
) {
  return useQuery({
    queryKey: ['admin', 'audit', entityType, entityId, limit, offset],
    queryFn: () => api.getAuditLog(entityType, entityId, limit, offset),
  })
}

export function useSyncStatus() {
  return useQuery({
    queryKey: ['admin', 'sync', 'status'],
    queryFn: () => api.getSyncStatus(),
    refetchInterval: 30_000,
  })
}

export function useForceSync() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (semester?: string) => api.forceSync(semester),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'sync'] })
    },
  })
}

export function useRule(ruleId: string, enabled = true) {
  return useQuery({
    queryKey: ['admin', 'rules', ruleId],
    queryFn: () => api.getRule(ruleId),
    enabled: enabled && !!ruleId,
  })
}

export function useUpdateRule() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ ruleId, dto }: { ruleId: string; dto: UpdateRuleDTO }) =>
      api.updateRule(ruleId, dto),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['admin', 'rules', variables.ruleId],
      })
      queryClient.invalidateQueries({ queryKey: ['criteria'] })
    },
  })
}
