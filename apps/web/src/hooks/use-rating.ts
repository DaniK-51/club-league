import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'

export function useRating(opts?: { period?: string; semester?: string }) {
  return useQuery({
    queryKey: ['rating', opts?.period ?? null, opts?.semester ?? null],
    queryFn: () => api.getRating(opts),
    staleTime: 5 * 60 * 1000,
  })
}
