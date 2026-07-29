import type { Client, schemas } from '@outception-com/client'
import { unwrap } from '@outception-com/client'
import * as WebBrowser from 'expo-web-browser'
import { Linking, UIManager } from 'react-native'
import { WEB_URL } from '@/utils/env'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']
export type NewsHeatmapTile = schemas['HeatmapTile']
export type NewsHeatmapResponse = schemas['HeatmapResponse']
export type NewsTemplate = schemas['NewsTemplate']

// Legal pages live on the web app; the native footer links out to them
// (mirrors the web footer, and satisfies the app stores' privacy-link rule).
/** Game cards render in a WebView — a native module only builds 22+ carry.
 * Checked at runtime so the SAME JS bundle stays safe when OTA'd to older
 * runtimes (they keep filtering the game cards out, exactly as before). */
export const hasGameWebView = (): boolean => {
  try {
    return UIManager.hasViewManagerConfig?.('RNCWebView') ?? false
  } catch {
    return false
  }
}

export const PRIVACY_URL = `${WEB_URL}/privacy`
export const TERMS_URL = `${WEB_URL}/terms`

/** The source's favicon, served from the web app's /news-icons (keyed by the
 * source id's family prefix, e.g. `bbc-world` → `bbc.png`). Mirrors the web
 * card's avatar. */
export const sourceIconUrl = (id: string): string =>
  `${WEB_URL}/news-icons/${id.split('-')[0]}.png`

/** A link that opens the web wall on this exact source in the sharer's language
 * (the web landing page reads `?card`/`?lang`). Shared from the mobile card so
 * recipients get the same rich preview + language as a web share. */
export const shareCardUrl = (sourceId: string, locale: string): string =>
  `${WEB_URL}/?card=${encodeURIComponent(sourceId)}&lang=${encodeURIComponent(
    locale,
  )}`

/** Compact, localized relative timestamp for headline kickers ("5m ago" in en,
 * localized elsewhere via Intl.RelativeTimeFormat). Clamps future/invalid dates
 * to "now". Pass `now` (e.g. from a ticking hook) so the label re-derives as
 * time passes, and `locale` for the reader's language. */
// Constructing Intl.RelativeTimeFormat is expensive on Hermes (locale
// resolution + data load) and timeAgo runs once per visible timeline row per
// card render — cache the formatters; only one per locale can ever exist.
const relativeFormatters = new Map<string, Intl.RelativeTimeFormat>()
const relativeFormatter = (
  locale: string | undefined,
): Intl.RelativeTimeFormat => {
  const key = locale ?? ''
  let fmt = relativeFormatters.get(key)
  if (!fmt) {
    // numeric 'auto' matches the web wording: a localized "now" for 0, and
    // "yesterday"/"last week" instead of "1 day ago"/"1 week ago".
    fmt = new Intl.RelativeTimeFormat(locale, {
      style: 'narrow',
      numeric: 'auto',
    })
    relativeFormatters.set(key, fmt)
  }
  return fmt
}

export const timeAgo = (
  ms: number,
  now: number = Date.now(),
  locale?: string,
): string => {
  const diff = now - ms
  const fmt = (value: number, unit: Intl.RelativeTimeFormatUnit): string => {
    try {
      return relativeFormatter(locale).format(-value, unit)
    } catch {
      // Intl unavailable — fall back to compact English.
      const suffix = {
        second: 's',
        minute: 'm',
        hour: 'h',
        day: 'd',
        week: 'w',
        month: 'mo',
        year: 'y',
      }
      return value === 0
        ? 'now'
        : `${value}${suffix[unit as keyof typeof suffix] ?? ''} ago`
    }
  }
  if (!Number.isFinite(diff) || diff < 60_000) return fmt(0, 'second')
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 60) return fmt(minutes, 'minute')
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return fmt(hours, 'hour')
  const days = Math.floor(hours / 24)
  if (days < 7) return fmt(days, 'day')
  // Weeks up to the 30-day month boundary (web's react-timeago buckets) —
  // stopping at 27 would render day 28-29 as "0 months ago".
  if (days < 30) return fmt(Math.floor(days / 7), 'week')
  // Months are 30-day buckets, but the year boundary is a real 365 days —
  // otherwise 12 × 30 would flip to "1y" five days early.
  if (days < 365) return fmt(Math.floor(days / 30), 'month')
  return fmt(Math.floor(days / 365), 'year')
}

/** Only absolute http(s) URLs leave the app — feed items are third-party data. */
export const isHttpUrl = (url: string | null | undefined): url is string =>
  !!url && /^https?:\/\/\S+$/i.test(url)

/**
 * Defense-in-depth for news links: items come from untrusted external feeds, so
 * only ever hand an http(s) URL to the OS link opener. A `javascript:`/`data:`
 * or arbitrary-scheme URL (e.g. a deep link) is ignored. The backend also
 * neutralizes these, so this is a second line.
 */
export const openExternalUrl = (url: string | null | undefined) => {
  if (isHttpUrl(url)) {
    // iOS rejects some universal links (YouTube Shorts when the YouTube app
    // declines them) — open those in the in-app browser instead.
    Linking.openURL(url).catch(() =>
      WebBrowser.openBrowserAsync(url).catch(() => undefined),
    )
  }
}

/** Hosts whose pages are never the article (video players), mirroring the
 * web + server lists. Google News links resolve server-side, so they try. */
const UNSUMMARIZABLE_HOSTS = new Set([
  'youtube.com',
  'www.youtube.com',
  'm.youtube.com',
  'youtu.be',
])

export const isSummarizable = (url: string | null | undefined): boolean => {
  if (!isHttpUrl(url)) return false
  const host = url.match(/^https?:\/\/([^/:?#]+)/i)?.[1]?.toLowerCase()
  return !!host && !UNSUMMARIZABLE_HOSTS.has(host)
}

export const newsApi = (outception: Client) => ({
  // One-tap AI article summary (cache-first server-side; kind 'teaser' when
  // the article was unreachable and the publisher's standfirst serves).
  summary: (url: string, lang: string) =>
    unwrap(
      outception.GET('/v1/news/summary', {
        params: { query: { url, lang } },
      }),
    ),
  // Fast prognosis: false = send the reader straight to the article.
  summaryAvailable: (url: string, lang: string) =>
    unwrap(
      outception.GET('/v1/news/summary/available', {
        params: { query: { url, lang } },
      }),
    ),
  sources: () => unwrap(outception.GET('/v1/news/sources')),
  // Metadata for just the given ids — what the deck needs to paint, without
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
  // The curated default "deck" for a fresh reader: an ordered list of source
  // ids (world, politics, science, … weather last), the same spread the web
  // wall seeds. Passing the device country tailors the sports slice to that
  // country's native sports/teams (e.g. Ireland → Gaelic football + hurling).
  defaultDeck: (country?: string) =>
    unwrap(
      outception.GET('/v1/news/default-deck', {
        params: { query: { country } },
      }),
    ),
  // latest=true so a card older than its (2 min) server freshness window
  // refetches live instead of re-serving stale cache. The server bounds this to
  // one outbound fetch per source per cooldown, so it can't hammer upstreams.
  source: (id: string, lang?: string) =>
    unwrap(
      outception.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { lang, latest: true } },
      }),
    ),
  search: (q: string, lang?: string) =>
    unwrap(
      outception.GET('/v1/news/search', { params: { query: { q, lang } } }),
    ),
  // Tiles for a `type: "heatmap"` roster source (see HeatmapCard).
  heatmap: (id: string) =>
    unwrap(
      outception.GET('/v1/news/heatmap/{heatmap_id}', {
        params: { path: { heatmap_id: id } },
      }),
    ),
})
