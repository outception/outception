/**
 * The deck composer: an ordered list of card ids for one reader.
 *
 * The server composes the default deck (country and city seeds, edge-cached);
 * this module mirrors that composition exactly, fixture-tested against the
 * server, and adds the reader's own deck on top. The precedence rule, written
 * down once:
 *
 * 1. the shared card when present, else the country card
 * 2. the briefing card for each profile the reader follows
 * 3. the rest in catalog order (follow order for a followed set)
 * 4. dedupe; drop unknown, disabled, hidden and `fallback` ids; cap
 *
 * No promoted splice: Products of the day is a normal catalog entry.
 */

import {
  BRIEFING_PREFIX,
  WEATHER_STRIP_ID,
  briefingCardId,
  countryCardId,
} from './card'

export const DECK_CAP = 120

export interface DeckEntry {
  id: string
  /** Ids spliced right after this entry, resolved per country. */
  injectAfter?: readonly string[]
  /** The country table that replaces the entry when the country has one. */
  swap?: string | null
  enabled?: boolean
  /** Month range, inclusive; wraps across the year end. */
  season?: readonly [number, number] | null
  countries?: readonly string[] | null
}

export type CountryTables = Readonly<
  Record<string, Readonly<Record<string, readonly string[]>>>
>

export interface DeckData {
  base: readonly DeckEntry[]
  countryTables?: CountryTables
  briefingProfileByCountry?: Readonly<Record<string, string>>
  defaultBriefingProfile?: string
}

export interface DeckFilters {
  known: (id: string) => boolean
  disabled: (id: string) => boolean
  fallback?: (id: string) => boolean
}

export interface DeckInput extends DeckFilters {
  country: string | null
  month: number
  sharedCard?: string | null
  briefingEnabled?: boolean
}

const countryTable = (
  data: DeckData,
  country: string | null,
  name: string,
): readonly string[] =>
  country === null ? [] : (data.countryTables?.[country]?.[name] ?? [])

const entryApplies = (entry: DeckEntry, inp: DeckInput): boolean => {
  if (entry.enabled === false) return false
  if (entry.season) {
    const [start, end] = entry.season
    const inside =
      start <= end
        ? start <= inp.month && inp.month <= end
        : !(end < inp.month && inp.month < start)
    if (!inside) return false
  }
  return (
    !entry.countries ||
    (inp.country !== null && entry.countries.includes(inp.country))
  )
}

/** An injected ref is a literal id or a country reference: `country:<table>`
 * resolves to the country's table (empty when the country has none),
 * `country:<table>|<id>` falls back to `<id>` when it has none, `country:news`
 * is the country card and `country:education` the country's education card. */
export const resolveRef = (
  ref: string,
  data: DeckData,
  country: string | null,
): readonly string[] => {
  if (!ref.startsWith('country:')) return [ref]
  const spec = ref.slice('country:'.length)
  const bar = spec.indexOf('|')
  const table = bar === -1 ? spec : spec.slice(0, bar)
  const fallback = bar === -1 ? '' : spec.slice(bar + 1)
  if (table === 'news') return country ? [countryCardId(country)] : []
  if (table === 'education')
    return country ? [`education-${country.toLowerCase()}`] : []
  const ids = countryTable(data, country, table)
  if (ids.length > 0) return ids
  return fallback ? [fallback] : []
}

/** Dedupe, drop unknown, disabled and fallback ids, pin the weather strip
 * last, cap. Briefing ids and the strip are never sources, so the source
 * filters do not apply to them. */
export const finalizeDeck = (
  cards: Iterable<string>,
  filters: DeckFilters,
  cap: number = DECK_CAP,
): string[] => {
  const seen = new Set<string>()
  const out: string[] = []
  for (const cardId of cards) {
    if (seen.has(cardId)) continue
    seen.add(cardId)
    if (cardId === WEATHER_STRIP_ID || cardId.startsWith(BRIEFING_PREFIX)) {
      out.push(cardId)
      continue
    }
    if (
      !filters.known(cardId) ||
      filters.disabled(cardId) ||
      filters.fallback?.(cardId)
    )
      continue
    out.push(cardId)
  }
  const hasWeather = out.includes(WEATHER_STRIP_ID)
  const content = out.filter((id) => id !== WEATHER_STRIP_ID).slice(0, cap)
  if (hasWeather) content.push(WEATHER_STRIP_ID)
  return content
}

/** The default deck for a visitor: country card first, then the ordered base
 * list with its country injections and swaps, deduped, filtered, the weather
 * strip last. Mirrors the server composer line for line. */
export const composeDefaultDeck = (
  data: DeckData,
  inp: DeckInput,
): string[] => {
  const cards: string[] = []
  if (inp.sharedCard) cards.push(inp.sharedCard)
  if (inp.country) cards.push(countryCardId(inp.country))
  if (inp.briefingEnabled) {
    const profile =
      data.briefingProfileByCountry?.[inp.country ?? ''] ??
      data.defaultBriefingProfile ??
      'news-junkie'
    cards.push(briefingCardId(profile))
  }
  for (const entry of data.base) {
    if (!entryApplies(entry, inp)) continue
    const swapped = entry.swap
      ? countryTable(data, inp.country, entry.swap)
      : []
    if (swapped.length > 0) cards.push(...swapped)
    else cards.push(entry.id)
    for (const ref of entry.injectAfter ?? []) {
      cards.push(...resolveRef(ref, data, inp.country))
    }
  }
  return finalizeDeck(cards, inp)
}

export interface ReaderDeckInput {
  /** The reader's followed ids, newest follow first. */
  followed: readonly string[]
  /** The server's default deck for this reader, used while nothing is followed. */
  seed?: readonly string[]
  /** True once the reader emptied the card set on purpose: never re-seed. */
  cleared?: boolean
  /** Unfollowed from a card: out of the deck until followed again. */
  hidden?: readonly string[]
  /** Ids the client cannot paint: metadata missing, feed failed, redirected. */
  dropped?: (id: string) => boolean
  /** A shared link's lead card: first, even when the reader hides it. */
  sharedCard?: string | null
  /** The reader's country card; first when present and no card was shared. */
  countryCard?: string | null
  briefingProfiles?: readonly string[]
  cap?: number
}

/** The reader's deck: the followed set, or the seed for a fresh visitor,
 * under the precedence rule above. */
export const composeDeck = (inp: ReaderDeckInput): string[] => {
  const base =
    inp.followed.length > 0 ? inp.followed : inp.cleared ? [] : (inp.seed ?? [])
  const hidden = new Set(inp.hidden ?? [])
  const dropped = inp.dropped ?? (() => false)
  const shared = inp.sharedCard ?? null
  const cards: string[] = []
  if (shared) cards.push(shared)
  else if (inp.countryCard && base.includes(inp.countryCard))
    cards.push(inp.countryCard)
  for (const profile of inp.briefingProfiles ?? [])
    cards.push(briefingCardId(profile))
  cards.push(...base)
  return finalizeDeck(
    cards,
    {
      known: (id) => id === shared || !dropped(id),
      disabled: (id) => id !== shared && hidden.has(id),
    },
    inp.cap ?? DECK_CAP,
  )
}

/** Whether the deck is still seeded (nothing followed, nothing cleared). */
export const isSeeded = (inp: Pick<ReaderDeckInput, 'followed' | 'cleared'>) =>
  inp.followed.length === 0 && !inp.cleared
