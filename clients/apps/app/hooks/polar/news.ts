import { usePolarClient } from '@/providers/PolarClientProvider'
import { schemas, unwrap } from '@polar-sh/client'
import { useQuery } from '@tanstack/react-query'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSort = 'hot' | 'new' | 'top' | 'rising'

export const useNewsSources = () => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => unwrap(polar.GET('/v1/news/sources')),
    staleTime: Infinity,
  })
}

export const useNewsSource = (
  id: string | undefined,
  sort: NewsSort = 'hot',
) => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['news', 'source', id, sort],
    queryFn: () =>
      unwrap(
        polar.GET('/v1/news/{source_id}', {
          params: { path: { source_id: id ?? '' }, query: { sort } },
        }),
      ),
    enabled: !!id,
    staleTime: 5 * 60_000,
  })
}
