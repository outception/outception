import { promotedApi } from '@/utils/promoted'
import { useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

/** The Promoted card currently running, or null. Runs are time-boxed in
 * hours or days, so a relaxed poll keeps every open wall within a couple of
 * minutes of a run starting or ending. */
export const usePromotedSlot = () =>
  useQuery({
    queryKey: ['promoted', 'active'],
    queryFn: () => promotedApi.active(),
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: defaultRetry,
  })
