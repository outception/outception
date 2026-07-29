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

export const useNewsTemplates = (enabled: boolean) =>
  useQuery({
    queryKey: ['news', 'templates'],
    queryFn: () => newsApi.templates(),
    staleTime: Infinity,
    retry: defaultRetry,
    enabled,
  })

export const useNewsSource = (
  id: string | null,
  sort: NewsSort = 'hot',
  lang?: string,
  active: boolean = true,
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
    // Only the top (visible) deck card polls — the two peeking neighbours
    // mount for the animation but don't need live refresh, and polling all
    // three tripled the wall's request volume for no visible benefit.
    refetchInterval: active ? 60_000 : false,
    // Coming back to the tab (or restoring the browser on mobile) must
    // re-pull the visible card immediately, even if the cache is <60s old —
    // mobile Safari restores can otherwise show a minutes-old snapshot.
    refetchOnWindowFocus: active ? 'always' : true,
    retry: defaultRetry,
  })

export const useNewsHeatmap = (id: string | null, active: boolean = true) =>
  useQuery({
    queryKey: ['news', 'heatmap', id],
    queryFn: () => newsApi.heatmap(id as string),
    enabled: !!id,
    // Quotes refresh server-side every 5 minutes; faster polling only
    // re-serves the same cache. Only the top deck card polls, like sources.
    staleTime: 300_000,
    refetchInterval: active ? 300_000 : false,
    // `true`, not `'always'`: returning from a tapped tile (each is a
    // target="_blank" link) must not force a refetch that re-sorts and visibly
    // reshuffles the treemap under the reader, matching the mobile hook.
    refetchOnWindowFocus: true,
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
