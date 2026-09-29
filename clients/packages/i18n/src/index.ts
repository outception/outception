import { useCallback } from 'react'

export { DEFAULT_LOCALE, SUPPORTED_LOCALES } from './config'
export type { AcceptedLocale, SupportedLocale } from './config'
export type { TranslateFn, TranslationKey, Translations } from './types'

import type { TranslationKey } from './types'

/** News topic (column) id → its translation key, shared by the web source
 * palette and the mobile topic chips so the filter labels localise identically. */
export const NEWS_COLUMN_KEYS = {
  news: 'news.columns.news',
  world: 'news.columns.world',
  sports: 'news.columns.sports',
  finance: 'news.columns.finance',
  science: 'news.columns.science',
  entertainment: 'news.columns.entertainment',
  tech: 'news.columns.tech',
  social: 'news.columns.social',
  betting: 'news.columns.betting',
  weather: 'news.columns.weather',
  lifestyle: 'news.columns.lifestyle',
  food: 'news.columns.food',
  travel: 'news.columns.travel',
  culture: 'news.columns.culture',
  faith: 'news.columns.faith',
  music: 'news.columns.music',
  gaming: 'news.columns.gaming',
  movies: 'news.columns.movies',
  tv: 'news.columns.tv',
  anime: 'news.columns.anime',
  books: 'news.columns.books',
  gadgets: 'news.columns.gadgets',
  cars: 'news.columns.cars',
  podcasts: 'news.columns.podcasts',
  cities: 'news.columns.cities',
  deals: 'news.columns.deals',
  property: 'news.columns.property',
} as const satisfies Record<string, TranslationKey>

/** The six broad topic groups the source-palette chips collapse the
 * fine-grained columns into - 25 chips crowded the dialog on both platforms.
 * Group ids are real column ids so NEWS_COLUMN_KEYS labels them; a column
 * absent from every group renders as its own chip. */
export const NEWS_TOPIC_GROUPS: readonly {
  id: keyof typeof NEWS_COLUMN_KEYS
  columns: readonly string[]
}[] = [
  { id: 'news', columns: ['news', 'world', 'cities', 'weather'] },
  { id: 'finance', columns: ['finance'] },
  { id: 'sports', columns: ['sports', 'betting'] },
  { id: 'tech', columns: ['tech', 'gadgets', 'science', 'social'] },
  {
    id: 'entertainment',
    columns: [
      'entertainment',
      'movies',
      'tv',
      'music',
      'anime',
      'gaming',
      'podcasts',
      'culture',
      'books',
    ],
  },
  {
    id: 'lifestyle',
    columns: [
      'lifestyle',
      'food',
      'travel',
      'cars',
      'deals',
      'property',
      'faith',
    ],
  },
]

/** Every column claimed by some group - the complement renders standalone. */
export const NEWS_GROUPED_COLUMNS: ReadonlySet<string> = new Set(
  NEWS_TOPIC_GROUPS.flatMap((g) => [...g.columns]),
)

import type { TranslateFn, Translations } from './types'
import en from './locales/en'

/** The app's strings. English is the only locale, bundled rather than loaded,
 * so this is a plain table lookup with no chunk, no merge and no cache. */
export function getTranslations(): Translations {
  return en
}

const pluralRules = new Intl.PluralRules('en')

/** CLDR plural category for a count ("one", "other"). Falls back to "other"
 * where Intl is unavailable. */
const pluralCategory = (count: number): string => {
  try {
    return pluralRules.select(count)
  } catch {
    return 'other'
  }
}

const interpolate = (
  template: string,
  interpolations?: Record<string, unknown>,
): string => {
  if (!interpolations) return template
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, k) => {
    const val = interpolations[k]
    return val === undefined ? `{${k}}` : String(val)
  })
}

/** Look one key up in the English table and fill in its placeholders.
 *
 * Plain function, not a hook: the lookup is what actually needs testing, and
 * `useTranslations` is only the stable binding React consumers hold. */
export const translate: TranslateFn = ((
  key: string,
  interpolations?: Record<string, unknown>,
) => {
  // Null-safe walk: an absent intermediate segment used to be
  // `undefined['x']`, a TypeError thrown from inside render - a white screen
  // rather than a missing string. The key type prevents this for literal
  // keys, but one dynamic key would take the app down.
  const value = key
    .split('.')
    .reduce<unknown>(
      (obj, k) =>
        obj == null ? undefined : (obj as Record<string, unknown>)[k],
      en as unknown as Record<string, unknown>,
    )

  if (
    typeof value === 'object' &&
    value !== null &&
    '_mode' in value &&
    (value as { _mode: string })._mode === 'plural'
  ) {
    const pluralObj = value as Record<string, string>
    const count = (interpolations as { count: number })?.count ?? 0
    // Exact match first (=0, =1, ...), then the CLDR category, then 'other'.
    const template =
      pluralObj[`=${count}`] ??
      pluralObj[pluralCategory(count)] ??
      pluralObj.other
    return interpolate(template.replace(/#/g, count.toString()), interpolations)
  }

  if (typeof value !== 'string') return key
  return interpolate(value, interpolations)
}) as TranslateFn

export const useTranslations = (): TranslateFn => useCallback(translate, [])
