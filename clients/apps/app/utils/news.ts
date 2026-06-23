import type { Client, schemas } from '@polar-sh/client'
import { unwrap } from '@polar-sh/client'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']
export type NewsSort = 'hot' | 'new' | 'top' | 'rising'

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
})
