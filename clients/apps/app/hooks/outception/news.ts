import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { hasGameWebView, newsApi } from '@/utils/news'
import { PERSISTED_GC_TIME } from '@/utils/queryPersist'
import { deviceCountry } from '@/utils/weather'
import type { NewsSourceMeta } from '@/utils/news'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useRef } from 'react'

export type {
  NewsHeatmapResponse,
  NewsHeatmapTile,
  NewsTemplate,
  NewsItem,
  NewsSearchResult,
  NewsSourceMeta,
  NewsSourceResponse,
} from '@/utils/news'

// Game cards need the WebView native module (builds 22+). On older runtimes
// this same bundle keeps dropping them - checked once at module scope because
// it cannot change at runtime, and kept out of an inline `select` so TanStack
// can reuse the filtered result instead of re-filtering (and structurally
// re-comparing) the whole roster on every render of every consumer.
const gamesSupported = hasGameWebView()

const selectSources = (list: NewsSourceMeta[]): NewsSourceMeta[] =>
  gamesSupported ? list : list.filter((s) => s.type !== 'game')

export const useNewsSearch = (query: string) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'search', query],
    queryFn: () => newsApi(outception).search(query),
    enabled: query.trim().length >= 2,
    // Surface failures as an error state in the results list, never as an
    // app-wide boundary (same reasoning as useNewsSource).
    throwOnError: false,
    staleTime: 30_000,
  })
}

export const useNewsSources = () => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi(outception).sources(),
    select: selectSources,
    throwOnError: false,
    staleTime: Infinity,
    gcTime: PERSISTED_GC_TIME,
  })
}

/** Metadata for just the card set's sources - the wall paints from this small
 * subset instead of downloading (and persisting) the multi-megabyte roster on
 * boot. The full roster loads lazily when the source browser opens.
 *
 * One entry, accumulated by id, deliberately not keyed on the id set: keying on
 * the set means every follow mints a fresh persisted blob (the growth this
 * replaced), and - worse - a follow made offline produces a key nothing has
 * ever cached, which would blank a card set whose headlines are all still on the
 * device. Merging keeps every source the reader has opened paintable offline. */
export const useWallSourceMetas = (ids: readonly string[]) => {
  const { outception } = useOutceptionClient()
  const queryClient = useQueryClient()
  const wanted = useMemo(() => [...ids].sort(), [ids])
  const query = useQuery({
    queryKey: ['news', 'source-metas'],
    queryFn: async () => {
      const known =
        queryClient.getQueryData<NewsSourceMeta[]>(['news', 'source-metas']) ??
        []
      const fetched = await newsApi(outception).sourceMetas(wanted)
      const byId = new Map(known.map((meta) => [meta.id, meta]))
      for (const meta of fetched) byId.set(meta.id, meta)
      return [...byId.values()]
    },
    enabled: wanted.length > 0,
    select: selectSources,
    throwOnError: false,
    staleTime: 5 * 60_000,
    gcTime: PERSISTED_GC_TIME,
  })
  // Refetch when the card set gains an id the merged set doesn't cover yet.
  // Coverage is read from the raw entry, not the selected one: `select`
  // drops game sources on runtimes without a WebView, which would otherwise
  // look uncovered forever. Each id is asked for once - the server omits ids
  // it no longer knows, so those would refetch on every card set change.
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

export const useNewsTemplates = (enabled: boolean) => {
  const { outception } = useOutceptionClient()
  const country = deviceCountry()
  return useQuery({
    queryKey: ['news', 'templates', country ?? ''],
    queryFn: () => newsApi(outception).templates(country ?? undefined),
    throwOnError: false,
    staleTime: Infinity,
    enabled,
  })
}

export const useDefaultCards = (enabled = true) => {
  const { outception } = useOutceptionClient()
  const country = deviceCountry()
  return useQuery({
    queryKey: ['news', 'default-cards', country],
    queryFn: () => newsApi(outception).defaultCards(country ?? undefined),
    enabled,
    throwOnError: false,
    staleTime: 5 * 60_000,
    gcTime: PERSISTED_GC_TIME,
  })
}

export const useNewsHeatmap = (id: string | undefined, active = true) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'heatmap', id],
    queryFn: () => newsApi(outception).heatmap(id ?? ''),
    enabled: !!id,
    // Quotes refresh on the server every 5 minutes (HEATMAP_INTERVAL_MS), so
    // polling faster only re-serves the same cache. Mirrors useNewsSource
    // otherwise: only the elevated card polls; peeks refetch when promoted.
    staleTime: 5 * 60_000,
    gcTime: PERSISTED_GC_TIME,
    refetchInterval: active ? 5 * 60_000 : false,
    refetchOnWindowFocus: true,
    // A dead quotes upstream must degrade to the card's error state, never the
    // app-wide boundary (same reasoning as useNewsSource).
    throwOnError: false,
  })
}

export const useNewsSource = (id: string | undefined, active = true) => {
  const { outception } = useOutceptionClient()
  const queryClient = useQueryClient()
  // Promotion re-arms the poll interval from zero, so a card that waited
  // behind the top one for minutes would paint its prefetched, stale headlines
  // for up to another minute. Pull it live on arrival instead (mirrors web).
  useEffect(() => {
    if (!active || !id) return
    const queryKey = ['news', 'source', id]
    const state = queryClient.getQueryState(queryKey)
    if (state?.dataUpdatedAt && Date.now() - state.dataUpdatedAt > 60_000) {
      void queryClient.refetchQueries({ queryKey, exact: true })
    }
  }, [active, id, queryClient])
  return useQuery({
    queryKey: ['news', 'source', id],
    queryFn: () => newsApi(outception).source(id ?? ''),
    enabled: !!id,
    // Poll the visible card ~every minute so the wall stays live; combined with
    // the 2 min server freshness window this lands a fresh fetch roughly every
    // couple of minutes (mirrors the web wall). Only polls while the app is
    // foregrounded (TanStack default), so it never refreshes in the background.
    staleTime: 60_000,
    // Restored-from-disk entries must outlive the persister's maxAge (see
    // utils/queryPersist.ts) or they're collected right after hydrating.
    gcTime: PERSISTED_GC_TIME,
    // Only the top card polls - the peeking neighbours mount for the swipe
    // animation and refresh when promoted (see NewsSourceCard `elevated`).
    refetchInterval: active ? 60_000 : false,
    // Returning from background shows fresh headlines immediately once the
    // data is past staleTime (AppState → focusManager in the provider). `true`,
    // not 'always': foregrounding also fires when the reader hops back from an
    // article or the share sheet, and an unconditional refetch there reshuffles
    // the card under them seconds after they left it.
    refetchOnWindowFocus: true,
    // The global default throws query errors into render, which would take the
    // whole app down to the error boundary when a single feed dies. The card
    // handles `isError` itself (markFailed → the source drops out of the card set),
    // exactly as the web wall does, so this one must resolve to an error state
    // rather than throw.
    throwOnError: false,
  })
}
