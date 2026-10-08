/**
 * Small news helpers both renderers share: the sort vocabulary, the paths a
 * client builds for the web app, and the compact relative timestamp.
 */

import { sourceFamily } from './card'

export type NewsSort = 'hot' | 'new' | 'top' | 'rising'
export const NEWS_SORTS: readonly NewsSort[] = ['hot', 'new', 'top', 'rising']

/** The card's icon, served by the web app and keyed by source family
 * (`bbc-world` uses `bbc.png`). */
export const sourceIconPath = (id: string): string =>
  `/news-icons/${encodeURIComponent(sourceFamily(id))}.png`

/** The wall opened on one card. The lead card stays in the query string so
 * the server-rendered unfurl keeps working. */
export const shareCardPath = (cardId: string): string =>
  `/?card=${encodeURIComponent(cardId)}`

export const wallPath = (topic?: string | null): string =>
  topic ? `/?topic=${encodeURIComponent(topic)}` : '/'

export const storyPath = (storyId: string): string =>
  `/story/${encodeURIComponent(storyId)}`

export const launchesPath = (): string => '/launches'

export const privacyPath = (): string => '/privacy'
export const termsPath = (): string => '/terms'

// Constructing a relative formatter is expensive (locale resolution plus
// data load) and `timeAgo` runs once per visible row per card render, so
// one formatter per locale is cached.
const relativeFormatters = new Map<string, Intl.RelativeTimeFormat>()
const relativeFormatter = (
  locale: string | undefined,
): Intl.RelativeTimeFormat => {
  const key = locale ?? ''
  let fmt = relativeFormatters.get(key)
  if (!fmt) {
    // numeric 'auto' reads "now" for 0 and "yesterday" rather than "1 day ago".
    fmt = new Intl.RelativeTimeFormat(locale, {
      style: 'narrow',
      numeric: 'auto',
    })
    relativeFormatters.set(key, fmt)
  }
  return fmt
}

const COMPACT_SUFFIX: Readonly<Record<string, string>> = {
  second: 's',
  minute: 'm',
  hour: 'h',
  day: 'd',
  week: 'w',
  month: 'mo',
  year: 'y',
}

/** Compact, localized relative timestamp for headline kickers ("5m ago").
 * Clamps future and invalid dates to "now". Pass `now` from a ticking hook
 * so the label re-derives as time passes. */
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
      // Intl unavailable: fall back to compact English.
      return value === 0 ? 'now' : `${value}${COMPACT_SUFFIX[unit] ?? ''} ago`
    }
  }
  if (!Number.isFinite(diff) || diff < 60_000) return fmt(0, 'second')
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 60) return fmt(minutes, 'minute')
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return fmt(hours, 'hour')
  const days = Math.floor(hours / 24)
  if (days < 7) return fmt(days, 'day')
  // Weeks up to the 30-day month boundary; stopping at 27 would render day
  // 28 and 29 as "0 months ago".
  if (days < 30) return fmt(Math.floor(days / 7), 'week')
  // Months are 30-day buckets, but the year boundary is a real 365 days.
  if (days < 365) return fmt(Math.floor(days / 30), 'month')
  return fmt(Math.floor(days / 365), 'year')
}
