import { usePolarClient } from '@/providers/PolarClientProvider'
import { newsApi, type NewsSort } from '@/utils/news'
import { useQuery } from '@tanstack/react-query'

export type {
  NewsItem,
  NewsSearchResult,
  NewsSort,
  NewsSourceMeta,
  NewsSourceResponse,
} from '@/utils/news'

export const useNewsSearch = (query: string) => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['news', 'search', query],
    queryFn: () => newsApi(polar).search(query),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
  })
}

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
