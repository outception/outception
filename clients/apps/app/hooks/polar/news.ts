import { usePolarClient } from '@/providers/PolarClientProvider'
import { newsApi, type NewsSort } from '@/utils/news'
import { useQuery } from '@tanstack/react-query'

export type {
  NewsItem,
  NewsSort,
  NewsSourceMeta,
  NewsSourceResponse,
} from '@/utils/news'

export const useNewsSources = () => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi(polar).sources(),
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
    queryFn: () => newsApi(polar).source(id ?? '', sort),
    enabled: !!id,
    staleTime: 5 * 60_000,
  })
}
