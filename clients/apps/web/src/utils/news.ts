import { api } from '@/utils/client'
import { schemas, unwrap } from '@outception-com/client'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']
export type NewsHeatmapTile = schemas['HeatmapTile']
export type NewsHeatmapResponse = schemas['HeatmapResponse']
export type NewsTemplate = schemas['NewsTemplate']

export type NewsSort = 'hot' | 'new' | 'top' | 'rising'

/**
 * Defense-in-depth for news links: items come from untrusted external feeds, so
 * only ever put an http(s) URL in an href. Returns undefined for anything else
 * (the anchor renders without an href, so a `javascript:`/`data:` URL can't be
 * clicked). The backend also neutralizes these, so this is a second line.
 */
export const safeExternalHref = (url: string | null | undefined) => {
  if (!url) return undefined
  try {
    const { protocol } = new URL(url)
    return protocol === 'http:' || protocol === 'https:' ? url : undefined
  } catch {
    return undefined
  }
}

/** Hosts whose pages are never the article (YouTube pages are a player), so
 * the summary endpoint refuses them (mirrors the server's list). A tap on those
 * opens the link. Google News links are resolved server-side, so they try. */
const UNSUMMARIZABLE_HOSTS = new Set([
  'youtube.com',
  'www.youtube.com',
  'm.youtube.com',
  'youtu.be',
])

export const isSummarizable = (url: string | null | undefined) => {
  if (!url) return false
  try {
    const { protocol, hostname } = new URL(url)
    if (protocol !== 'http:' && protocol !== 'https:') return false
    return !UNSUMMARIZABLE_HOSTS.has(hostname)
  } catch {
    return false
  }
}

export const newsApi = {
  sources: () => unwrap(api.GET('/v1/news/sources')),
  // Metadata for a specific id set (the wall's deck). Hand-rolled fetch: the
  // `ids` filter isn't in the generated client. Falls back to the full roster
  // so the wall degrades to slower, never to blank. Credentialed like the
  // generated client so it rides the same preconnected socket pool — browsers
  // keep anonymous and credentialed cross-origin connections apart.
  sourceMetas: async (ids: readonly string[]): Promise<NewsSourceMeta[]> => {
    try {
      const url = new URL(`${process.env.NEXT_PUBLIC_API_URL}/v1/news/sources`)
      url.searchParams.set('ids', ids.join(','))
      const res = await fetch(url, { credentials: 'include' })
      if (!res.ok) throw new Error(String(res.status))
      return (await res.json()) as NewsSourceMeta[]
    } catch {
      return unwrap(api.GET('/v1/news/sources'))
    }
  },
  // Starter templates: persona bundles, country-resolved server-side.
  templates: () => unwrap(api.GET('/v1/news/templates')),
  // Source ids to seed an empty "Your deck". Passing the reader's country
  // tailors the sports slice to that country's native sports/teams (e.g.
  // Ireland → Gaelic football + hurling). Hand-rolled fetch: this endpoint
  // isn't in the generated client.
  defaultDeck: async (country?: string): Promise<string[]> => {
    try {
      const url = new URL(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/news/default-deck`,
      )
      if (country) url.searchParams.set('country', country)
      const res = await fetch(url, { credentials: 'include' })
      return res.ok ? ((await res.json()) as string[]) : []
    } catch {
      return []
    }
  },
  source: (id: string, latest = false, sort: NewsSort = 'hot', lang?: string) =>
    unwrap(
      api.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { latest, sort, lang } },
      }),
    ),
  // Tiles for a `type: "heatmap"` roster source (see HeatmapCard).
  heatmap: (id: string) =>
    unwrap(
      api.GET('/v1/news/heatmap/{heatmap_id}', {
        params: { path: { heatmap_id: id } },
      }),
    ),
  search: (q: string, lang?: string) =>
    unwrap(api.GET('/v1/news/search', { params: { query: { q, lang } } })),
}
