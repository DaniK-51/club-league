import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { CreatePeriodDTO, UpdatePeriodDTO } from '@/lib/types'

export function usePeriods(enabled = true) {
  return useQuery({
    queryKey: ['admin', 'periods'],
    queryFn: () => api.getPeriods(),
    enabled,
    retry: false,
  })
}

function useInvalidatePeriods() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: ['admin', 'periods'] })
    queryClient.invalidateQueries({ queryKey: ['rating'] })
    queryClient.invalidateQueries({ queryKey: ['reports'] })
  }
}

export function useCreatePeriod() {
  const invalidate = useInvalidatePeriods()
  return useMutation({
    mutationFn: (dto: CreatePeriodDTO) => api.createPeriod(dto),
    onSuccess: invalidate,
  })
}

export function useUpdatePeriod() {
  const invalidate = useInvalidatePeriods()
  return useMutation({
    mutationFn: ({ id, dto }: { id: string; dto: UpdatePeriodDTO }) =>
      api.updatePeriod(id, dto),
    onSuccess: invalidate,
  })
}

export function useDeletePeriod() {
  const invalidate = useInvalidatePeriods()
  return useMutation({
    mutationFn: (id: string) => api.deletePeriod(id),
    onSuccess: invalidate,
  })
}
