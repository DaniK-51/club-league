import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { ModerateReportDTO } from '@/lib/types'

export function useAllReports() {
  return useQuery({
    queryKey: ['reports', 'all'],
    queryFn: () => api.getReports(),
  })
}

export function useReportComments(reportId: string, enabled = true) {
  return useQuery({
    queryKey: ['reports', reportId, 'comments'],
    queryFn: () => api.getReportComments(reportId),
    enabled: enabled && !!reportId,
  })
}

export function useModerateReport() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: ModerateReportDTO }) =>
      api.moderateReport(id, dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useCompleteReport() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.completeReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useArchiveReports() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (period: string) => api.archiveReports(period),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}
