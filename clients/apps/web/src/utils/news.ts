import { api } from '@/utils/client'
import { schemas, unwrap } from '@outception-com/client'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']

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

export const newsApi = {
  sources: () => unwrap(api.GET('/v1/news/sources')),
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
      const res = await fetch(url)
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
  search: (q: string, lang?: string) =>
    unwrap(api.GET('/v1/news/search', { params: { query: { q, lang } } })),
}
