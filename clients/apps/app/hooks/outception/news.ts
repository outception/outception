import { useLocale } from '@/providers/LocaleProvider'
import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { newsApi } from '@/utils/news'
import { deviceCountry, weatherApi } from '@/utils/weather'
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
    staleTime: 30_000,
  })
}

export const useNewsSources = () => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi(outception).sources(),
    staleTime: Infinity,
  })
}

export const useDefaultDeck = (enabled = true) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'default-deck'],
    queryFn: () => newsApi(outception).defaultDeck(),
    enabled,
    staleTime: Infinity,
  })
}

/** Weather for the reader's device region (its capital), the mobile analogue of
 * the web card. Disabled when the device reports no region, so the card shows
 * "unavailable" rather than fetching a default city. */
export const useWeather = () => {
  const country = deviceCountry()
  return useQuery({
    queryKey: ['news', 'weather', country],
    queryFn: () => weatherApi.forecast({ country: country ?? undefined }),
    enabled: country !== null,
    staleTime: 15 * 60_000,
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
    staleTime: 5 * 60_000,
  })
}
