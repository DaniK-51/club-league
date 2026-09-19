import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function usePublicPeriods() {
  return useQuery({
    queryKey: ['periods', 'public'],
    queryFn: () => api.getPublicPeriods(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
