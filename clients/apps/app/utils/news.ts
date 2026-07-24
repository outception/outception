import type { Client, schemas } from '@outception-com/client'
import { unwrap } from '@outception-com/client'
import { Linking } from 'react-native'

export type NewsSourceMeta = schemas['SourceMeta']
export type NewsSourceResponse = schemas['SourceResponse']
export type NewsItem = schemas['NewsItem']
export type NewsSearchResult = schemas['NewsSearchResponse']

const WEB_URL =
  process.env.EXPO_PUBLIC_OUTCEPTION_WEB_URL ?? 'http://127.0.0.1:3000'

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
export const timeAgo = (
  ms: number,
  now: number = Date.now(),
  locale?: string,
): string => {
  const diff = now - ms
  const fmt = (value: number, unit: Intl.RelativeTimeFormatUnit): string => {
    try {
      return new Intl.RelativeTimeFormat(locale, {
        style: 'narrow',
        // 'auto' yields a localized "now" for 0; 'always' keeps "5m ago" etc.
        numeric: value === 0 ? 'auto' : 'always',
      }).format(-value, unit)
    } catch {
      // Intl unavailable — fall back to compact English.
      const suffix = {
        second: 's',
        minute: 'm',
        hour: 'h',
        day: 'd',
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
  if (days < 30) return fmt(days, 'day')
  // Months are 30-day buckets, but the year boundary is a real 365 days —
  // otherwise 12 × 30 would flip to "1y" five days early.
  if (days < 365) return fmt(Math.floor(days / 30), 'month')
  return fmt(Math.floor(days / 365), 'year')
}

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
  // The curated default "deck" for a fresh reader: an ordered list of source
  // ids (world, politics, science, … weather last), the same spread the web
  // wall seeds. Mobile resolves these ids against the full source list.
  defaultDeck: () => unwrap(outception.GET('/v1/news/default-deck')),
  source: (id: string, lang?: string) =>
    unwrap(
      outception.GET('/v1/news/{source_id}', {
        params: { path: { source_id: id }, query: { lang } },
      }),
    ),
  search: (q: string, lang?: string) =>
    unwrap(
      outception.GET('/v1/news/search', { params: { query: { q, lang } } }),
    ),
})
