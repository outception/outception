import type { Client, schemas } from '@outception-com/client'
import { unwrap } from '@outception-com/client'
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

export const newsApi = (outception: Client) => ({
  sources: () => unwrap(outception.GET('/v1/news/sources')),
  source: (id: string, sort: NewsSort = 'hot') =>
    unwrap(
      outception.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { sort } },
      }),
    ),
  search: (q: string) =>
    unwrap(outception.GET('/v1/news/search', { params: { query: { q } } })),
  followed: () => unwrap(outception.GET('/v1/news/followed')),
  followedFeed: () => unwrap(outception.GET('/v1/news/followed/feed')),
  follow: (id: string) =>
    outception.PUT('/v1/news/followed/{source_id}', {
      params: { path: { source_id: id } },
    }),
  unfollow: (id: string) =>
    outception.DELETE('/v1/news/followed/{source_id}', {
      params: { path: { source_id: id } },
    }),
})
