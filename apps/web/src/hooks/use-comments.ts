import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function usePostComment(reportId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: string) => api.postReportComment(reportId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports', reportId, 'comments'] })
    },
  })
}
