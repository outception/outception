import { useLocale } from '@/providers/LocaleProvider'
import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { hasGameWebView, newsApi } from '@/utils/news'
import { PERSISTED_GC_TIME } from '@/utils/queryPersist'
import { deviceCountry } from '@/utils/weather'
import { useQuery } from '@tanstack/react-query'

export type {
  NewsHeatmapResponse,
  NewsHeatmapTile,
  NewsTemplate,
  NewsItem,
  NewsSearchResult,
  NewsSourceMeta,
  NewsSourceResponse,
} from '@/utils/news'

export const useNewsSearch = (query: string) => {
  const { outception } = useOutceptionClient()
  const locale = useLocale()
  return useQuery({
    queryKey: ['news', 'search', query, locale],
    queryFn: () => newsApi(outception).search(query, locale),
    enabled: query.trim().length >= 2,
    // Surface failures as an error state in the results list, never as an
    // app-wide crash (see useNewsSource).
    throwOnError: false,
    staleTime: 30_000,
  })
}

export const useNewsSources = () => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi(outception).sources(),
    // Game cards need the WebView native module (builds 22+). On older
    // runtimes this same bundle keeps dropping them — checked at runtime so
    // OTA updates stay safe across runtimes.
    select: (list) =>
      hasGameWebView() ? list : list.filter((s) => s.type !== 'game'),
    throwOnError: false,
    staleTime: Infinity,
    gcTime: PERSISTED_GC_TIME,
  })
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

export const useDefaultDeck = (enabled = true) => {
  const { outception } = useOutceptionClient()
  const country = deviceCountry()
  return useQuery({
    queryKey: ['news', 'default-deck', country],
    queryFn: () => newsApi(outception).defaultDeck(country ?? undefined),
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
  const locale = useLocale()
  return useQuery({
    // Headlines are machine-translated into the reader's language server-side
    // (no-op for English), so the card renders translated on first paint.
    queryKey: ['news', 'source', id, locale],
    queryFn: () => newsApi(outception).source(id ?? '', locale),
    enabled: !!id,
    // Poll the visible card ~every minute so the wall stays live; combined with
    // the 2 min server freshness window this lands a fresh fetch roughly every
    // couple of minutes (mirrors the web wall). Only polls while the app is
    // foregrounded (TanStack default), so it never refreshes in the background.
    staleTime: 60_000,
    // Restored-from-disk entries must outlive the persister's maxAge (see
    // utils/queryPersist.ts) or they're collected right after hydrating.
    gcTime: PERSISTED_GC_TIME,
    // Only the top card polls; the peeking neighbours mount for the swipe
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
    // handles `isError` itself (markFailed → the source drops out of the deck),
    // exactly as the web wall does, so this one must resolve to an error state
    // rather than throw.
    throwOnError: false,
  })
}
