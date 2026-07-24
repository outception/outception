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
// to mirror direction-sensitive UI (e.g. the swipe deck) for these readers.
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
