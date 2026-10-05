import type { Client, schemas } from '@outception-com/client'
import { unwrap } from '@outception-com/client'
import {
  isHttpUrl,
  shareCardPath,
  sourceIconPath,
} from '@outception-com/news-core'
import * as WebBrowser from 'expo-web-browser'
import { Linking } from 'react-native'
import { WEB_URL } from '@/utils/env'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']
export type NewsHeatmapTile = schemas['HeatmapTile']
export type NewsHeatmapResponse = schemas['HeatmapResponse']
export type NewsTemplate = schemas['NewsTemplate']
export type {
  BriefingItem,
  Card,
  CardItem,
  CardKind,
  SignalState,
} from '@outception-com/news-core'
export { isHttpUrl, isSummarizable, timeAgo } from '@outception-com/news-core'

// Legal pages live on the web app; the native footer links out to them
// (mirrors the web footer, and satisfies the app stores' privacy-link rule).
export const PRIVACY_URL = `${WEB_URL}/privacy`
export const TERMS_URL = `${WEB_URL}/terms`

/** The card's icon, served by the web app and keyed by source family. */
export const sourceIconUrl = (id: string): string =>
  `${WEB_URL}${sourceIconPath(id)}`

/** A link that opens the web wall on this exact card, so recipients get the
 * same rich preview as a web share. */
export const shareCardUrl = (cardId: string): string =>
  `${WEB_URL}${shareCardPath(cardId)}`

/**
 * Defense-in-depth for news links: items come from untrusted external feeds, so
 * only ever hand an http(s) URL to the OS link opener. A `javascript:`/`data:`
 * or arbitrary-scheme URL (e.g. a deep link) is ignored. The backend also
 * neutralizes these, so this is a second line.
 */
export const openExternalUrl = (url: string | null | undefined) => {
  if (isHttpUrl(url)) {
    // iOS rejects some universal links (YouTube Shorts when the YouTube app
    // declines them) - open those in the in-app browser instead.
    Linking.openURL(url).catch(() =>
      WebBrowser.openBrowserAsync(url).catch(() => undefined),
    )
  }
}

export const newsApi = (outception: Client) => ({
  // One-tap AI article summary (cache-first server-side; kind 'teaser' when
  // the article was unreachable and the publisher's standfirst serves).
  summary: (url: string) =>
    unwrap(outception.GET('/v1/news/summary', { params: { query: { url } } })),
  // Fast prognosis: false = send the reader straight to the article.
  summaryAvailable: (url: string) =>
    unwrap(
      outception.GET('/v1/news/summary/available', {
        params: { query: { url } },
      }),
    ),
  sources: () => unwrap(outception.GET('/v1/news/sources')),
  // Metadata for just the given ids - what the card set needs to paint, without
  // downloading the multi-megabyte roster (only the source browser needs that).
  sourceMetas: (ids: readonly string[]) =>
    unwrap(
      outception.GET('/v1/news/sources', {
        params: { query: { ids: ids.join(',') } },
      }),
    ),
  // Starter templates: persona bundles, country-resolved server-side.
  templates: (country?: string) =>
    unwrap(
      outception.GET('/v1/news/templates', {
        params: { query: { country } },
      }),
    ),
  // The curated default "card set" for a fresh reader: an ordered list of source
  // ids (world, politics, science, … weather last), the same spread the web
  // wall seeds. Passing the device country tailors the sports slice to that
  // country's native sports/teams (e.g. Ireland → Gaelic football + hurling).
  defaultCards: (country?: string) =>
    unwrap(
      outception.GET('/v1/news/default-cards', {
        params: { query: { country } },
      }),
    ),
  // latest=true so a card older than its (2 min) server freshness window
  // refetches live instead of re-serving stale cache. The server bounds this to
  // one outbound fetch per source per cooldown, so it can't hammer upstreams.
  source: (id: string) =>
    unwrap(
      outception.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { latest: true } },
      }),
    ),
  search: (q: string) =>
    unwrap(outception.GET('/v1/news/search', { params: { query: { q } } })),
  briefingProfiles: () => unwrap(outception.GET('/v1/news/briefing/profiles')),
  briefingHistory: (profile: string, days = 2) =>
    unwrap(
      outception.GET('/v1/news/briefing/{profile}/history', {
        params: { path: { profile }, query: { days } },
      }),
    ),
  // One push a morning with the profile's briefing; the device token is the
  // only identity, there is no account.
  subscribePush: (profile: string, token: string) =>
    unwrap(
      outception.POST('/v1/news/briefing/{profile}/subscribe', {
        params: { path: { profile } },
        body: { kind: 'app', endpoint: token },
      }),
    ),
  unsubscribePush: (profile: string, token: string) =>
    unwrap(
      outception.DELETE('/v1/news/briefing/{profile}/subscribe', {
        params: { path: { profile } },
        body: { endpoint: token },
      }),
    ),
  briefing: (profile: string) =>
    unwrap(
      outception.GET('/v1/news/briefing/{profile}', {
        params: { path: { profile } },
      }),
    ),
  // Tiles for a `type: "heatmap"` roster source (see HeatmapCard).
  heatmap: (id: string) =>
    unwrap(
      outception.GET('/v1/news/heatmap/{heatmap_id}', {
        params: { path: { heatmap_id: id } },
      }),
    ),
})
