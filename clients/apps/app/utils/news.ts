import type { Client, schemas } from '@polar-sh/client'
import { unwrap } from '@polar-sh/client'
import { Linking } from 'react-native'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']
export type NewsSort = 'hot' | 'new' | 'top' | 'rising'

/**
 * Defense-in-depth for news links: items come from untrusted external feeds, so
 * only ever hand an http(s) URL to the OS link opener. A `javascript:`/`data:`
 * or arbitrary-scheme URL (e.g. a deep link) is ignored. The backend also
 * neutralizes these, so this is a second line.
 */
export const openExternalUrl = (url: string | null | undefined) => {
  if (url && /^https?:\/\/\S+$/i.test(url)) {
    void Linking.openURL(url)
  }
}

export const newsApi = (polar: Client) => ({
  sources: () => unwrap(polar.GET('/v1/news/sources')),
  source: (id: string, sort: NewsSort = 'hot') =>
    unwrap(
      polar.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { sort } },
      }),
    ),
  search: (q: string) =>
    unwrap(polar.GET('/v1/news/search', { params: { query: { q } } })),
  followed: () => unwrap(polar.GET('/v1/news/followed')),
  followedFeed: () => unwrap(polar.GET('/v1/news/followed/feed')),
  follow: (id: string) =>
    polar.PUT('/v1/news/followed/{source_id}', {
      params: { path: { source_id: id } },
    }),
  unfollow: (id: string) =>
    polar.DELETE('/v1/news/followed/{source_id}', {
      params: { path: { source_id: id } },
    }),
})
