import { useLocale } from '@/providers/locale'
import { newsApi, type NewsSort } from '@/utils/news'
import { useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

export const useDefaultDeck = (enabled = true) =>
  useQuery({
    queryKey: ['news', 'default-deck'],
    queryFn: () => newsApi.defaultDeck(),
    enabled,
    staleTime: 300_000,
    retry: defaultRetry,
  })

export const useNewsSources = () =>
  useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi.sources(),
    staleTime: Infinity,
    retry: defaultRetry,
  })

export const useNewsSource = (
  id: string | null,
  sort: NewsSort = 'hot',
  lang?: string,
) =>
  useQuery({
    queryKey: ['news', 'source', id, sort, lang ?? 'en'],
    queryFn: () => newsApi.source(id as string, false, sort, lang),
    enabled: !!id,
    // Headlines are live; refresh each card ~every minute so the wall stays
    // current without a manual page reload. Only polls while the tab is
    // focused (default), so background tabs don't hammer the API.
    staleTime: 60_000,
    refetchInterval: 60_000,
    retry: defaultRetry,
  })

export const useNewsSearch = (query: string) => {
  const locale = useLocale()
  return useQuery({
    queryKey: ['news', 'search', query, locale],
    queryFn: () => newsApi.search(query, locale),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
    retry: defaultRetry,
  })
}
