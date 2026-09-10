import { useLocale } from '@/providers/locale'
import { getClientCountry } from '@/utils/i18n/shared'
import { newsApi, type NewsSort, type NewsSourceMeta } from '@/utils/news'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef } from 'react'
import { defaultRetry } from './retry'

/** While the server reports translations pending the top card re-polls at
 * this cadence. Measured on the live API: a cold card serves originals at the
 * 1 s soft wait and the translations land 1-2 s after that, so a 4 s poll
 * left readers looking at English for most of 6 s. Polls are cache-first on
 * the server (one Redis mget), so the faster cadence costs nothing upstream. */
/** Re-poll fast at first, then ease off. The server soft-waits 2.5 s, so a
 * card that STILL reports pending is one the model is running long on: the
 * first re-ask is cheap and usually lands it, while a genuinely slow provider
 * settles onto the slower cadence instead of hammering. */
const TRANSLATION_POLL_STEPS_MS = [400, 700, 1_100] as const
const TRANSLATION_POLL_MS = 1_500
const translationPollDelayMs = (count: number): number =>
  TRANSLATION_POLL_STEPS_MS[count - 1] ?? TRANSLATION_POLL_MS
/** How many fast polls a card may fire while the server reports translations
 * pending, before falling back to the normal cadence (~24 s of fast polling). */
const TRANSLATION_POLL_LIMIT = 16

export const useDefaultCards = (enabled = true) => {
  // The reader's IP country (geo cookie) tailors the sports slice of the card set.
  const country = getClientCountry() ?? undefined
  return useQuery({
    queryKey: ['news', 'default-cards', country],
    queryFn: () => newsApi.defaultCards(country),
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

/** Metadata for just the card set's sources - the wall paints from this small
 * subset instead of parsing the multi-megabyte full roster on boot (the
 * roster loads lazily when the search palette opens).
 *
 * One entry, accumulated by id, deliberately NOT keyed on the id set. Keying
 * on the set made every follow, hide, or starter-template tap mint a new query
 * and refetch metadata for the WHOLE card set - applying a 60-source template then
 * starring three more sources was four full round trips - and left every
 * superseded set sitting in the cache. Mirrors the mobile hook. */
export const useWallSourceMetas = (ids: readonly string[]) => {
  const queryClient = useQueryClient()
  const wanted = useMemo(() => [...ids].sort(), [ids])
  const query = useQuery({
    queryKey: ['news', 'source-metas'],
    queryFn: async () => {
      const known =
        queryClient.getQueryData<NewsSourceMeta[]>(['news', 'source-metas']) ??
        []
      const fetched = await newsApi.sourceMetas(wanted)
      const byId = new Map(known.map((meta) => [meta.id, meta]))
      for (const meta of fetched) byId.set(meta.id, meta)
      return [...byId.values()]
    },
    enabled: wanted.length > 0,
    staleTime: 300_000,
    retry: defaultRetry,
  })
  // Refetch only when the card set gains an id the merged set does not cover.
  // Each id is asked for once: the server omits ids it no longer knows, and
  // those would otherwise refetch on every card set change.
  const asked = useRef(new Set<string>())
  const { dataUpdatedAt, isError, refetch } = query
  useEffect(() => {
    if (wanted.length === 0 || isError) return
    const known =
      queryClient.getQueryData<NewsSourceMeta[]>(['news', 'source-metas']) ?? []
    const have = new Set(known.map((meta) => meta.id))
    const missing = wanted.filter(
      (id) => !have.has(id) && !asked.current.has(id),
    )
    if (missing.length === 0) return
    for (const id of missing) asked.current.add(id)
    void refetch()
  }, [wanted, dataUpdatedAt, isError, refetch, queryClient])
  return query
}

/**
 * Headlines for the whole card set at once, for the zoom view.
 *
 * The deck asks per card because it only ever shows one at a time. The zoom
 * view shows all of them together, so asking card by card would mean 60+
 * requests to paint one screen. The batch route reads cache in a single
 * round trip and never triggers a fetch, so this stays cheap even at the
 * 120-card ceiling.
 *
 * Deliberately NOT polled. The deck's visible card keeps itself fresh; a
 * mosaic of sixty is a browsing view, and re-pulling all of it on a timer
 * would multiply the wall's request volume for headlines nobody is reading
 * closely.
 */
export const useWallBatch = (ids: readonly string[], enabled: boolean) => {
  const locale = useLocale()
  return useQuery({
    queryKey: ['news', 'batch', ids.join(','), locale],
    queryFn: () => newsApi.batch(ids, locale),
    enabled: enabled && ids.length > 0,
    staleTime: 60_000,
    retry: defaultRetry,
  })
}

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
    // The card set mounts the previous and upcoming cards as ~24px peeks behind a
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
    // Only the top (visible) card polls - the two peeking neighbours
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
        : translationPollDelayMs(pendingPolls.current.count)
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
    // re-serves the same cache. Only the top card polls, like sources.
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
  // Keyed on the query text and language so a new search, or a language
  // switch, starts its poll budget afresh.
  const pollKey = `${query}|${locale}`
  const pendingPolls = useRef({ key: pollKey, at: 0, count: 0 })
  return useQuery({
    queryKey: ['news', 'search', query, locale],
    queryFn: () => newsApi.search(query, locale),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
    retry: defaultRetry,
    // Search is cache-first on the server and never waits on a model, so the
    // first search in a language comes back in the original text with
    // `translationsPending` set. Re-ask on the same short cadence the card set
    // cards use so the reader sees their language without retyping. Bounded
    // and counted per fetch, like the card: a server that keeps reporting
    // pending must not hold the palette at a 1.5 s refetch all session.
    refetchInterval: (q) => {
      if (!q.state.data?.translationsPending) {
        pendingPolls.current = { key: pollKey, at: 0, count: 0 }
        return false
      }
      if (pendingPolls.current.key !== pollKey) {
        pendingPolls.current = { key: pollKey, at: 0, count: 0 }
      }
      const at = Math.max(q.state.dataUpdatedAt, q.state.errorUpdatedAt)
      if (at !== pendingPolls.current.at) {
        pendingPolls.current = {
          key: pollKey,
          at,
          count: pendingPolls.current.count + 1,
        }
      }
      return pendingPolls.current.count > TRANSLATION_POLL_LIMIT
        ? false
        : translationPollDelayMs(pendingPolls.current.count)
    },
  })
}
