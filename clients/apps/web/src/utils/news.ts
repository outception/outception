import { api } from '@/utils/client'
import { schemas, unwrap } from '@polar-sh/client'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']

export type NewsSort = 'hot' | 'new' | 'top' | 'rising'

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
