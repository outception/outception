import { api } from '@/utils/client'
import { unwrap } from '@outception-com/client'
import type { NewsSort } from '@outception-com/news-core'

export type {
  BriefingItem,
  Card,
  CardItem,
  CardKind,
  HeatmapTile as NewsHeatmapTile,
  NewsItem,
  NewsSort,
  NewsTemplate,
  SignalState,
  SourceMeta as NewsSourceMeta,
} from '@outception-com/news-core'
export { isSummarizable, safeExternalHref } from '@outception-com/news-core'

type NewsSourceMeta = import('@outception-com/news-core').SourceMeta

export const newsApi = {
  sources: () => unwrap(api.GET('/v1/news/sources')),
  // Metadata for a specific id set (the wall's card set). Hand-rolled fetch:
  // the `ids` filter isn't in the generated client. Falls back to the full
  // roster so the wall degrades to slower, never to blank. Credentialed like
  // the generated client so it rides the same preconnected socket pool.
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
  // Starters: persona bundles, country-resolved server-side.
  templates: () => unwrap(api.GET('/v1/news/templates')),
  // Card ids to seed an empty card set. Passing the reader's country tailors
  // the sports slice to that country's native sports and teams. Hand-rolled
  // fetch: this endpoint isn't in the generated client.
  defaultCards: async (country?: string): Promise<string[]> => {
    try {
      const url = new URL(
        `${process.env.NEXT_PUBLIC_API_URL}/v1/news/default-cards`,
      )
      if (country) url.searchParams.set('country', country)
      const res = await fetch(url, { credentials: 'include' })
      return res.ok ? ((await res.json()) as string[]) : []
    } catch {
      return []
    }
  },
  source: (id: string, latest = false, sort: NewsSort = 'hot') =>
    unwrap(
      api.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { latest, sort } },
      }),
    ),
  // Tiles for a `type: "heatmap"` catalog entry (see HeatmapCard).
  heatmap: (id: string) =>
    unwrap(
      api.GET('/v1/news/heatmap/{heatmap_id}', {
        params: { path: { heatmap_id: id } },
      }),
    ),
  search: (q: string) =>
    unwrap(api.GET('/v1/news/search', { params: { query: { q } } })),
  // One card contract: the envelope for a feed, a table, a briefing or the
  // weather strip, with the signal state and the update stamp.
  card: (id: string, latest = false, attachedTo?: string) =>
    unwrap(
      api.GET('/v1/cards/{card_id}', {
        params: { path: { card_id: id }, query: { latest, attachedTo } },
      }),
    ),
  briefingProfiles: () => unwrap(api.GET('/v1/news/briefing/profiles')),
  credits: () => unwrap(api.GET('/v1/news/credits')),
  // A typed city resolved to a city card, through the catalog or a keyless
  // geocoder on the server.
  city: (q: string) =>
    unwrap(api.GET('/v1/news/cities', { params: { query: { q } } })),
  briefing: (profile: string) =>
    unwrap(
      api.GET('/v1/news/briefing/{profile}', { params: { path: { profile } } }),
    ),
  // The last days of a briefing, newest first, for "since yesterday".
  briefingHistory: (profile: string, days = 2) =>
    unwrap(
      api.GET('/v1/news/briefing/{profile}/history', {
        params: { path: { profile }, query: { days } },
      }),
    ),
  // One push a morning with the profile's briefing; the endpoint is the only
  // identity, there is no account.
  subscribePush: (
    profile: string,
    body: {
      kind: 'web'
      endpoint: string
      keys: { p256dh: string; auth: string }
    },
  ) =>
    unwrap(
      api.POST('/v1/news/briefing/{profile}/subscribe', {
        params: { path: { profile } },
        body,
      }),
    ),
  unsubscribePush: (profile: string, endpoint: string) =>
    unwrap(
      api.DELETE('/v1/news/briefing/{profile}/subscribe', {
        params: { path: { profile } },
        body: { endpoint },
      }),
    ),
  story: (id: string) =>
    unwrap(
      api.GET('/v1/news/story/{story_id}', {
        params: { path: { story_id: id } },
      }),
    ),
}
