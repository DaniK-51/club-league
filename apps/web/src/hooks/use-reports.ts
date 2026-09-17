import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { CreateReportDTO, ModerateReportDTO } from '@/lib/types'

// === Queries ===

export function useCriteria(semester?: string, category?: string) {
  return useQuery({
    queryKey: ['criteria', semester, category],
    queryFn: () => api.getCriteria(semester, category),
    staleTime: 10 * 60 * 1000,
  })
}

export function useReports() {
  return useQuery({
    queryKey: ['reports'],
    queryFn: () => api.getReports(),
  })
}

export function useReport(id: string) {
  return useQuery({
    queryKey: ['reports', id],
    queryFn: () => api.getReport(id),
    enabled: !!id,
  })
}

export function useReportComments(reportId: string, enabled = true) {
  return useQuery({
    queryKey: ['reports', reportId, 'comments'],
    queryFn: () => api.getReportComments(reportId),
    enabled: enabled && !!reportId,
  })
}

// === Mutations ===

function useInvalidateReports() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: ['reports'] })
}

export function useCreateReport() {
  const invalidate = useInvalidateReports()
  return useMutation({
    mutationFn: (dto: CreateReportDTO) => api.createReport(dto),
    onSuccess: invalidate,
  })
}

export function useSubmitReport() {
  const invalidate = useInvalidateReports()
  return useMutation({
    mutationFn: (id: string) => api.submitReport(id),
    onSuccess: invalidate,
  })
}

export function useDeleteReport() {
  const invalidate = useInvalidateReports()
  return useMutation({
    mutationFn: (id: string) => api.deleteReport(id),
    onSuccess: invalidate,
  })
}

export function useModerateReport() {
  const invalidate = useInvalidateReports()
  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: ModerateReportDTO }) =>
      api.moderateReport(id, dto),
    onSuccess: invalidate,
  })
}

export function useCompleteReport() {
  const invalidate = useInvalidateReports()
  return useMutation({
    mutationFn: (id: string) => api.completeReport(id),
    onSuccess: invalidate,
  })
}

export function useArchiveReports() {
  const invalidate = useInvalidateReports()
  return useMutation({
    mutationFn: (period: string) => api.archiveReports(period),
    onSuccess: invalidate,
  })
}
