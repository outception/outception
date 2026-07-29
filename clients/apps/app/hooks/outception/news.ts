import { useLocale } from '@/providers/LocaleProvider'
import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { newsApi } from '@/utils/news'
import { deviceCountry } from '@/utils/weather'
import { useQuery } from '@tanstack/react-query'

export type {
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
    throwOnError: false,
    staleTime: Infinity,
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
  })
}

export const useNewsSource = (id: string | undefined) => {
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
    refetchInterval: 60_000,
    // The global default throws query errors into render, which would take the
    // whole app down to the error boundary when a single feed dies. The card
    // handles `isError` itself (markFailed → the source drops out of the deck),
    // exactly as the web wall does, so this one must resolve to an error state
    // rather than throw.
    throwOnError: false,
  })
}
