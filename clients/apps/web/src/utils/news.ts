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
  source: (id: string, latest = false, sort: NewsSort = 'hot') =>
    unwrap(
      api.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { latest, sort } },
      }),
    ),
  batch: (sources: string[]) =>
    unwrap(api.POST('/v1/news/batch', { body: { sources } })),
  search: (q: string) =>
    unwrap(api.GET('/v1/news/search', { params: { query: { q } } })),
  followed: () => unwrap(api.GET('/v1/news/followed')),
  followedFeed: () => unwrap(api.GET('/v1/news/followed/feed')),
  follow: (id: string) =>
    api.PUT('/v1/news/followed/{source_id}', {
      params: { path: { source_id: id } },
    }),
  unfollow: (id: string) =>
    api.DELETE('/v1/news/followed/{source_id}', {
      params: { path: { source_id: id } },
    }),
}
