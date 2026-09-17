import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function useSetCalculation(reportId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: { method: 'auto' | 'manual'; manualPoints?: number }) =>
      api.setCalculation(reportId, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', reportId] })
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}
