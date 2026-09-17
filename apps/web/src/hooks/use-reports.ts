import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { CreateReportDTO } from '@/lib/types'

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

export function useCreateReport() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: CreateReportDTO) => api.createReport(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useSubmitReport() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.submitReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}

export function useDeleteReport() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => api.deleteReport(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    },
  })
}
