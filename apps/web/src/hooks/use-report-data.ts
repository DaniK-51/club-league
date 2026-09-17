import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function useUpdateReportData(reportId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { reportData: Record<string, unknown> }) =>
      api.updateReport(reportId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', reportId] })
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}
