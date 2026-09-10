export const SUPPORTED_LOCALES = [
  'en',
  'nl',
  'fr',
  'sv',
  'es',
  'de',
  'hu',
  'it',
  'pt',
  'pt-PT',
  'ko',
  'ja',
  'tr',
  'pl',
  'ru',
  'uk',
  'ar',
  'he',
  'fa',
  'hi',
  'bn',
  'ur',
  'zh-Hans',
  'zh-Hant',
  'id',
  'ms',
  'tl',
  'vi',
  'th',
  'cs',
  'sk',
  'sl',
  'ro',
  'bg',
  'sr',
  'sq',
  'el',
  'da',
  'nb',
  'fi',
  'et',
  'lv',
  'lt',
  'ga',
  'ca',
  'eu',
  'hr',
] as const
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]
export const DEFAULT_LOCALE = 'en' satisfies SupportedLocale

export type TranslatedLocale = Exclude<SupportedLocale, typeof DEFAULT_LOCALE>

// Right-to-left scripts among the supported locales. Used to set <html dir> and
// to mirror direction-sensitive UI (e.g. the swipe card set) for these readers.
export const RTL_LOCALES = ['ar', 'he', 'fa', 'ur'] as const

/** Whether a locale is written right-to-left (matches on the primary language,
 * so region variants like `ar-EG` still count). */
export const isRtlLocale = (locale: string): boolean =>
  (RTL_LOCALES as readonly string[]).includes(locale.split('-')[0])

/** The writing direction for a locale, for `dir` attributes. */
export const getLocaleDir = (locale: string): 'ltr' | 'rtl' =>
  isRtlLocale(locale) ? 'rtl' : 'ltr'

// Expand bare language codes to include region variants,
// but keep region-specific codes (like future 'pt-BR') exact
type Alpha =
  | 'A'
  | 'B'
  | 'C'
  | 'D'
  | 'E'
  | 'F'
  | 'G'
  | 'H'
  | 'I'
  | 'J'
  | 'K'
  | 'L'
  | 'M'
  | 'N'
  | 'O'
  | 'P'
  | 'Q'
  | 'R'
  | 'S'
  | 'T'
  | 'U'
  | 'V'
  | 'W'
  | 'X'
  | 'Y'
  | 'Z'

type ResolveBCP47<T extends string> = T extends `${string}-${string}`
  ? T
  : T | `${T}-${Alpha}${Alpha}`

export type AcceptedLocale = ResolveBCP47<SupportedLocale>

export const LOCALE_NAMES: Record<SupportedLocale, string> = {
  en: 'English',
  nl: 'Dutch',
  sv: 'Swedish',
  es: 'Spanish',
  fr: 'French',
  de: 'German',
  hu: 'Hungarian',
  it: 'Italian',
  pt: 'Portuguese (Brazil)',
  'pt-PT': 'Portuguese (Portugal)',
  ko: 'Korean',
  ja: 'Japanese',
  tr: 'Turkish',
  pl: 'Polish',
  ru: 'Russian',
  uk: 'Ukrainian',
  ar: 'Arabic',
  he: 'Hebrew',
  fa: 'Persian',
  hi: 'Hindi',
  bn: 'Bengali',
  ur: 'Urdu',
  'zh-Hans': 'Chinese (Simplified)',
  'zh-Hant': 'Chinese (Traditional)',
  id: 'Indonesian',
  ms: 'Malay',
  tl: 'Filipino',
  vi: 'Vietnamese',
  th: 'Thai',
  cs: 'Czech',
  sk: 'Slovak',
  sl: 'Slovenian',
  ro: 'Romanian',
  bg: 'Bulgarian',
  sr: 'Serbian',
  sq: 'Albanian',
  el: 'Greek',
  da: 'Danish',
  nb: 'Norwegian',
  fi: 'Finnish',
  et: 'Estonian',
  lv: 'Latvian',
  lt: 'Lithuanian',
  ga: 'Irish',
  ca: 'Catalan',
  eu: 'Basque',
  hr: 'Croatian',
}

/** BCP-47 tags whose supported locale cannot be reached by exact match or by
 * the bare primary language. Real devices report Chinese as `zh-Hans-CN`,
 * `zh-CN` or `zh-Hant-TW`, and Filipino as `fil-PH`; the supported list holds
 * `zh-Hans`, `zh-Hant` and `tl`, so every one of those reduced to `zh`/`fil`,
 * matched nothing, and a phone set to 简体中文 opened the app in English even
 * though the translations ship. Longest prefix wins, so `zh-Hant-HK` picks
 * Traditional before the bare `zh` entry. */
const LOCALE_ALIASES: readonly (readonly [string, SupportedLocale])[] = [
  ['zh-hant', 'zh-Hant'],
  ['zh-hans', 'zh-Hans'],
  // Region implies script where the script subtag is absent.
  ['zh-tw', 'zh-Hant'],
  ['zh-hk', 'zh-Hant'],
  ['zh-mo', 'zh-Hant'],
  ['zh-cn', 'zh-Hans'],
  ['zh-sg', 'zh-Hans'],
  // Bare `zh` is Simplified in practice, and matches the CLDR default.
  ['zh', 'zh-Hans'],
  // CLDR and both mobile platforms say `fil`; the UI locale is named `tl`.
  ['fil', 'tl'],
]

/** Reduce a BCP-47 code to a supported UI locale: an exact match (e.g.
 * `pt-PT`) as-is, else a known alias (`zh-Hans-CN` → `zh-Hans`, `fil-PH` →
 * `tl`), else the bare primary language if we support it (`de-DE` → `de`),
 * else null. Shared by the app and the web so device and browser detection
 * cannot drift apart. */
export function toSupportedLocale(code: string): SupportedLocale | null {
  const list = SUPPORTED_LOCALES as readonly string[]
  if (list.includes(code)) return code as SupportedLocale
  const lower = code.toLowerCase()
  for (const [prefix, locale] of LOCALE_ALIASES) {
    if (lower === prefix || lower.startsWith(`${prefix}-`)) return locale
  }
  const primary = code.split('-')[0]
  if (list.includes(primary)) return primary as SupportedLocale
  return null
}
