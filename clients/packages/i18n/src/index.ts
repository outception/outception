import { useCallback } from 'react'

export {
  DEFAULT_LOCALE,
  getLocaleDir,
  isRtlLocale,
  LOCALE_NAMES,
  RTL_LOCALES,
  SUPPORTED_LOCALES,
} from './config'
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
 * fine-grained columns into — 25 chips crowded the dialog on both platforms.
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
    columns: ['lifestyle', 'food', 'travel', 'cars', 'deals', 'property', 'faith'],
  },
]

/** Every column claimed by some group — the complement renders standalone. */
export const NEWS_GROUPED_COLUMNS: ReadonlySet<string> = new Set(
  NEWS_TOPIC_GROUPS.flatMap((g) => [...g.columns]),
)

import type { AcceptedLocale, SupportedLocale } from './config'
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from './config'
import type {
  DeepPartialLocale,
  LocaleShape,
  TranslateFn,
  Translations,
} from './types'

export function getTranslationLocale(locale: AcceptedLocale): SupportedLocale {
  if (SUPPORTED_LOCALES.includes(locale as SupportedLocale)) {
    return locale as SupportedLocale
  }
  const language = locale.split('-')[0].toLowerCase()
  if (SUPPORTED_LOCALES.includes(language as SupportedLocale)) {
    return language as SupportedLocale
  }
  return DEFAULT_LOCALE
}

export function isAcceptedLocale(value: string): value is AcceptedLocale {
  // Exact supported code (incl. script/region variants like 'zh-Hans', 'pt-PT').
  if (SUPPORTED_LOCALES.includes(value as SupportedLocale)) return true
  // Otherwise a region variant of a supported bare language ('de-DE' → 'de').
  const language = value.split('-')[0].toLowerCase()
  return SUPPORTED_LOCALES.includes(language as SupportedLocale)
}

export function isSupportedLocale(locale: string): locale is SupportedLocale {
  return SUPPORTED_LOCALES.includes(locale as SupportedLocale)
}

import en from './locales/en'
import nl from './locales/nl'
import fr from './locales/fr'
import sv from './locales/sv'
import es from './locales/es'
import de from './locales/de'
import hu from './locales/hu'
import it from './locales/it'
import pt from './locales/pt'
import ptPT from './locales/pt-PT'
import ko from './locales/ko'
import ja from './locales/ja'
import tr from './locales/tr'
import pl from './locales/pl'
import ru from './locales/ru'
import uk from './locales/uk'
import ar from './locales/ar'
import he from './locales/he'
import fa from './locales/fa'
import hi from './locales/hi'
import bn from './locales/bn'
import ur from './locales/ur'
import zhHans from './locales/zh-Hans'
import zhHant from './locales/zh-Hant'
import id from './locales/id'
import ms from './locales/ms'
import tl from './locales/tl'
import vi from './locales/vi'
import th from './locales/th'
import cs from './locales/cs'
import sk from './locales/sk'
import sl from './locales/sl'
import ro from './locales/ro'
import bg from './locales/bg'
import sr from './locales/sr'
import sq from './locales/sq'
import el from './locales/el'
import da from './locales/da'
import nb from './locales/nb'
import fi from './locales/fi'
import et from './locales/et'
import lv from './locales/lv'
import lt from './locales/lt'
import ga from './locales/ga'
import ca from './locales/ca'
import eu from './locales/eu'
import hr from './locales/hr'

type LocalesRecord = { en: LocaleShape<Translations> } & Record<
  Exclude<SupportedLocale, 'en'>,
  DeepPartialLocale<LocaleShape<Translations>>
>

const translations: LocalesRecord = {
  en,
  nl,
  fr,
  sv,
  es,
  de,
  hu,
  it,
  pt,
  'pt-PT': ptPT,
  ko,
  ja,
  tr,
  pl,
  ru,
  uk,
  ar,
  he,
  fa,
  hi,
  bn,
  ur,
  'zh-Hans': zhHans,
  'zh-Hant': zhHant,
  id,
  ms,
  tl,
  vi,
  th,
  cs,
  sk,
  sl,
  ro,
  bg,
  sr,
  sq,
  el,
  da,
  nb,
  fi,
  et,
  lv,
  lt,
  ga,
  ca,
  eu,
  hr,
}

const isAtomicLeaf = (v: unknown): boolean => {
  if (v === null || typeof v !== 'object') return true
  if ('_mode' in v) return true
  const value = (v as { value?: unknown }).value
  if (typeof value === 'string') return true
  return false
}

const deepMerge = (base: unknown, override: unknown): unknown => {
  if (override === undefined) return base
  if (isAtomicLeaf(override) || isAtomicLeaf(base)) return override
  const result: Record<string, unknown> = {
    ...(base as Record<string, unknown>),
  }
  for (const key of Object.keys(override as Record<string, unknown>)) {
    result[key] = deepMerge(
      (base as Record<string, unknown>)[key],
      (override as Record<string, unknown>)[key],
    )
  }
  return result
}

const mergedCache = new Map<SupportedLocale, Translations>()

// CLDR plural category for the locale ("one", "few", "many", "other", …).
// Cached: constructing Intl.PluralRules per call is expensive and t() runs on
// every render. Falls back to "other" where Intl is unavailable.
const pluralRulesCache = new Map<string, Intl.PluralRules | null>()

const pluralCategory = (locale: string, count: number): string => {
  let rules = pluralRulesCache.get(locale)
  if (rules === undefined) {
    try {
      rules = new Intl.PluralRules(locale)
    } catch {
      rules = null
    }
    pluralRulesCache.set(locale, rules)
  }
  return rules ? rules.select(count) : 'other'
}

export function getTranslations(
  locale: AcceptedLocale = DEFAULT_LOCALE,
): Translations {
  const translationLocale = getTranslationLocale(locale)
  if (translationLocale === DEFAULT_LOCALE) return en
  const cached = mergedCache.get(translationLocale)
  if (cached) return cached
  const merged = deepMerge(en, translations[translationLocale]) as Translations
  mergedCache.set(translationLocale, merged)
  return merged
}

export const useTranslations = (locale: AcceptedLocale): TranslateFn => {
  return useCallback(
    ((key: string, interpolations?: Record<string, unknown>) => {
      const translations = getTranslations(locale)

      // Null-safe walk: an absent intermediate segment used to be
      // `undefined['x']`, a TypeError thrown from inside render — a white
      // screen rather than a missing string. The key type prevents this for
      // literal keys, but one dynamic key would take the app down.
      const value = key
        .split('.')
        .reduce<unknown>(
          (obj, k) =>
            obj == null ? undefined : (obj as Record<string, unknown>)[k],
          translations,
        )

      if (typeof value !== 'string' && typeof value !== 'object') return key

      // Handle plural objects
      if (
        typeof value === 'object' &&
        value !== null &&
        '_mode' in value &&
        (value as { _mode: string })._mode === 'plural'
      ) {
        const pluralObj = value as Record<string, string>
        const count = (interpolations as { count: number })?.count ?? 0

        // Exact match first (=0, =1, …), then the locale's CLDR category, then
        // 'other'. Without the CLDR step every Slavic, Baltic and Arabic reader
        // always got the 'other' form, which is grammatically wrong for them.
        const template =
          pluralObj[`=${count}`] ??
          pluralObj[pluralCategory(locale, count)] ??
          pluralObj.other

        // Replace # with count, then handle other interpolations
        let result = template.replace(/#/g, count.toString())

        if (interpolations) {
          result = result.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, k) => {
            const val = interpolations[k]
            return val === undefined ? `{${k}}` : String(val)
          })
        }

        return result
      }

      // Handle annotated entries — extract the value string
      const template =
        typeof value === 'object' &&
        value !== null &&
        'value' in value &&
        typeof (value as { value: unknown }).value === 'string'
          ? (value as { value: string }).value
          : (value as string)

      if (!interpolations) {
        return template
      }

      return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, k) => {
        const val = interpolations[k]
        return val === undefined ? `{${k}}` : String(val)
      })
    }) as TranslateFn,
    [locale],
  )
}
