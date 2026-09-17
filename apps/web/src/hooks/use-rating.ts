import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function useRating(semester?: string) {
  return useQuery({
    queryKey: ['rating', semester],
    queryFn: () => api.getRating(semester),
    staleTime: 5 * 60 * 1000,
  })
}
