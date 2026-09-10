import { getClientCountry } from '@/utils/i18n/shared'
import { newsApi, type NewsSort, type NewsSourceMeta } from '@/utils/news'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef } from 'react'
import { defaultRetry } from './retry'

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
 * Deliberately NOT polled. The deck's visible card keeps itself fresh; re-
 * pulling every card on a timer would multiply the wall's request volume for
 * headlines nobody is reading closely.
 */
export const useWallBatch = (ids: readonly string[], enabled: boolean) =>
  useQuery({
    queryKey: ['news', 'batch', ids.join(',')],
    queryFn: () => newsApi.batch(ids),
    enabled: enabled && ids.length > 0,
    staleTime: 60_000,
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
  active: boolean = true,
  enabled: boolean = true,
) => {
  const queryClient = useQueryClient()
  // Promotion re-arms the poll interval from zero, so a card that waited
  // behind the top one for minutes would paint its prefetched, stale headlines
  // for up to another minute. Pull it live on arrival instead.
  useEffect(() => {
    if (!active || !id) return
    const queryKey = ['news', 'source', id, sort]
    const state = queryClient.getQueryState(queryKey)
    if (state?.dataUpdatedAt && Date.now() - state.dataUpdatedAt > 60_000) {
      void queryClient.refetchQueries({ queryKey, exact: true })
    }
  }, [active, id, sort, queryClient])
  return useQuery({
    queryKey: ['news', 'source', id, sort],
    // latest=true so a card older than its (2 min) freshness window actually
    // refetches live instead of re-serving the stale cache. The server bounds
    // this to one outbound fetch per source per cooldown, so polling here can't
    // hammer the upstreams no matter how many readers view the same source.
    queryFn: () => newsApi.source(id as string, true, sort),
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
    // Only the top (visible) card polls - the two peeking neighbours mount for
    // the animation but don't need live refresh, and polling all three tripled
    // the wall's request volume for no visible benefit.
    refetchInterval: active ? 60_000 : false,
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

export const useNewsSearch = (query: string) =>
  useQuery({
    queryKey: ['news', 'search', query],
    queryFn: () => newsApi.search(query),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
    retry: defaultRetry,
  })
