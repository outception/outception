import { useLocale } from '@/providers/locale'
import { getClientCountry } from '@/utils/i18n/shared'
import { newsApi, type NewsSort } from '@/utils/news'
import {
  keepPreviousData,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { defaultRetry } from './retry'

/** How many 4s polls a card may fire while the server reports translations
 * pending, before falling back to the normal cadence. */
const TRANSLATION_POLL_LIMIT = 6

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

export const useNewsSources = (enabled = true) =>
  useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi.sources(),
    staleTime: Infinity,
    retry: defaultRetry,
    enabled,
  })

/** Metadata for just the deck's sources - the wall paints from this small
 * subset instead of parsing the multi-megabyte full roster on boot (the
 * roster loads lazily when the search palette opens). */
export const useWallSourceMetas = (ids: readonly string[]) =>
  useQuery({
    queryKey: ['news', 'source-metas', [...ids].sort().join(',')],
    queryFn: () => newsApi.sourceMetas(ids),
    enabled: ids.length > 0,
    staleTime: 300_000,
    retry: defaultRetry,
    // A follow changes the id set: keep the current cards on screen while the
    // new set loads instead of unmounting the deck (and its position) for a
    // loader flash.
    placeholderData: keepPreviousData,
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
  enabled: boolean = true,
) => {
  // Counted per fetch, not per call: refetchInterval is re-evaluated on every
  // observer update, so a plain counter would spend the budget without a single
  // request going out. Keyed on the card, language and activity so a language
  // switch or a swipe back starts the fast polls afresh.
  const pollKey = `${id}|${sort}|${lang ?? 'en'}|${active}`
  const pendingPolls = useRef({ key: pollKey, at: 0, count: 0 })
  const queryClient = useQueryClient()
  // Promotion re-arms the poll interval from zero, so a card that waited
  // behind the top one for minutes would paint its prefetched, stale headlines
  // for up to another minute. Pull it live on arrival instead.
  useEffect(() => {
    if (!active || !id) return
    const queryKey = ['news', 'source', id, sort, lang ?? 'en']
    const state = queryClient.getQueryState(queryKey)
    if (state?.dataUpdatedAt && Date.now() - state.dataUpdatedAt > 60_000) {
      void queryClient.refetchQueries({ queryKey, exact: true })
    }
  }, [active, id, sort, lang, queryClient])
  return useQuery({
    queryKey: ['news', 'source', id, sort, lang ?? 'en'],
    // latest=true so a card older than its (2 min) freshness window actually
    // refetches live instead of re-serving the stale cache. The server bounds
    // this to one outbound fetch per source per cooldown, so polling here can't
    // hammer the upstreams no matter how many readers view the same source.
    queryFn: () => newsApi.source(id as string, true, sort, lang),
    // The deck mounts the previous and upcoming cards as ~24px peeks behind a
    // mask; fetching a full headline feed for each tripled the wall's request
    // volume for pixels nobody can read. Callers pass `false` until a card has
    // been the top one, then keep passing `true` so its cache survives and
    // swiping back is instant.
    enabled: !!id && enabled,
    // Poll each visible card ~every minute so the wall stays current without a
    // manual reload; combined with the 2 min server freshness window this lands
    // a live refresh roughly every couple of minutes. Only polls while the tab
    // is focused (default), so background tabs don't hammer the API.
    staleTime: 60_000,
    // Only the top (visible) deck card polls - the two peeking neighbours
    // mount for the animation but don't need live refresh, and polling all
    // three tripled the wall's request volume for no visible benefit. While
    // the server is still translating some headlines it says so, and the card
    // re-polls in seconds instead of showing originals for a whole minute.
    refetchInterval: (query) => {
      if (!query.state.data?.translationsPending) {
        pendingPolls.current = { key: pollKey, at: 0, count: 0 }
        return active ? 60_000 : false
      }
      // Bounded, and only for the card being read: a server that keeps
      // reporting pending translations must not hold every mounted card at a
      // 4s refetch for the rest of the session. Failed polls count too -
      // otherwise an API outage would hold the card at the fast cadence.
      if (!active) return false
      if (pendingPolls.current.key !== pollKey) {
        pendingPolls.current = { key: pollKey, at: 0, count: 0 }
      }
      const at = Math.max(query.state.dataUpdatedAt, query.state.errorUpdatedAt)
      if (at !== pendingPolls.current.at) {
        pendingPolls.current = {
          key: pollKey,
          at,
          count: pendingPolls.current.count + 1,
        }
      }
      return pendingPolls.current.count > TRANSLATION_POLL_LIMIT
        ? 60_000
        : 4_000
    },
    // Coming back to the tab (or restoring the browser on mobile) must
    // re-pull the visible card immediately, even if the cache is <60s old -
    // mobile Safari restores can otherwise show a minutes-old snapshot.
    refetchOnWindowFocus: active ? 'always' : true,
    retry: defaultRetry,
  })
}

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
