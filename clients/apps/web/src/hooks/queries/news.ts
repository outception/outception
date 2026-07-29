import { useLocale } from '@/providers/locale'
import { getClientCountry } from '@/utils/i18n/shared'
import { newsApi, type NewsSort } from '@/utils/news'
import { useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

export const useDefaultDeck = (enabled = true) => {
  // The reader's IP country (geo cookie) tailors the sports slice of the deck.
  const country = getClientCountry() ?? undefined
  return useQuery({
    queryKey: ['news', 'default-deck', country],
    queryFn: () => newsApi.defaultDeck(country),
    enabled,
    staleTime: 300_000,
    retry: defaultRetry,
  })
}

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
    // latest=true so a card older than its (2 min) freshness window actually
    // refetches live instead of re-serving the stale cache. The server bounds
    // this to one outbound fetch per source per cooldown, so polling here can't
    // hammer the upstreams no matter how many readers view the same source.
    queryFn: () => newsApi.source(id as string, true, sort, lang),
    enabled: !!id,
    // Poll each visible card ~every minute so the wall stays current without a
    // manual reload; combined with the 2 min server freshness window this lands
    // a live refresh roughly every couple of minutes. Only polls while the tab
    // is focused (default), so background tabs don't hammer the API.
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
