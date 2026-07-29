import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  isAcceptedLocale,
  SUPPORTED_LOCALES,
} from '@outception-com/i18n'

const SUPPORTED = SUPPORTED_LOCALES as readonly string[]

/** Reduce a BCP-47 code to the supported UI locale we translate to: an exact
 * supported locale (e.g. `pt-PT`) as-is, else the bare primary language if we
 * support it (`de-DE` → `de`, `en-US` → `en`, `pt-BR` → `pt`), else null. */
function toSupportedLocale(code: string): AcceptedLocale | null {
  if (SUPPORTED.includes(code)) return code as AcceptedLocale
  const primary = code.split('-')[0]
  if (SUPPORTED.includes(primary)) return primary as AcceptedLocale
  return null
}

// Cookie the middleware sets from Cloudflare's CF-IPCountry, so client
// components can resolve the reader's country locale (and flag) after hydration.
export const GEO_COUNTRY_COOKIE = 'oc-geo-country'

// Cookie holding the reader's explicit language choice (the flag picker),
// which overrides auto-detection — e.g. an English speaker in Japan.
export const LOCALE_OVERRIDE_COOKIE = 'oc-locale'

// Cookie holding the country flag the reader picked alongside an English
// variant (e.g. "IE" for "English (Ireland)"), so the pill keeps showing their
// flag even though the content locale is plain `en`.
export const FLAG_OVERRIDE_COOKIE = 'oc-flag'

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]+)`))
  if (!match) return null
  try {
    return decodeURIComponent(match[1])
  } catch {
    // A malformed %-sequence (only reachable if a cookie is hand-edited) must
    // not throw — this runs during render via getClientCountry.
    return match[1]
  }
}

export function parseAcceptLanguageHeader(
  acceptLanguageHeader: string | null,
): { code: string; q: number }[] {
  if (!acceptLanguageHeader) return []

  return acceptLanguageHeader
    .split(',')
    .map((lang) => {
      const [code, qValue] = lang.trim().split(';q=')
      return {
        code: code.trim(),
        q: qValue ? parseFloat(qValue) : 1,
      }
    })
    .sort((a, b) => b.q - a.q)
}

/** The first supported locale in an Accept-Language header (full tag, then
 * bare primary language), or null when none is supported. */
export function getBrowserLocale(
  acceptLanguageHeader: string | null,
): AcceptedLocale | null {
  for (const { code } of parseAcceptLanguageHeader(acceptLanguageHeader)) {
    const supported = toSupportedLocale(code)
    if (supported) return supported
  }
  return null
}

export function getLocaleFromAcceptLanguageHeader(
  acceptLanguageHeader: string | null,
): AcceptedLocale {
  return getBrowserLocale(acceptLanguageHeader) ?? DEFAULT_LOCALE
}

// ISO-3166 country → the supported UI locale spoken there, used only as a
// fallback when the reader expressed no supported non-English preference; every
// unmapped country falls through to English. Officially multilingual countries
// (Ireland, Belgium, Switzerland, Canada, India, Philippines, Malaysia, Hong
// Kong, Pakistan, UAE, Indonesia, plus e.g. Luxembourg, South Africa, Singapore)
// are deliberately left UNMAPPED so they default to English — a neutral lingua
// franca rather than picking one of their language communities over another —
// while still showing their own country flag. Speakers of a supported language
// still get it via their browser locale, which takes precedence over this
// country fallback.
const COUNTRY_LOCALE: Record<string, AcceptedLocale> = {
  NL: 'nl',
  FR: 'fr',
  SE: 'sv',
  DE: 'de',
  AT: 'de',
  HU: 'hu',
  IT: 'it',
  BR: 'pt',
  PT: 'pt-PT',
  KR: 'ko',
  JP: 'ja',
  TR: 'tr',
  // Spanish: Spain + Latin America
  ES: 'es',
  MX: 'es',
  AR: 'es',
  CO: 'es',
  CL: 'es',
  PE: 'es',
  VE: 'es',
  EC: 'es',
  GT: 'es',
  CU: 'es',
  BO: 'es',
  DO: 'es',
  HN: 'es',
  PY: 'es',
  SV: 'es', // El Salvador (country) → Spanish
  NI: 'es',
  CR: 'es',
  PA: 'es',
  UY: 'es',
  // Added languages, mapped to their primary country.
  PL: 'pl',
  RU: 'ru',
  BY: 'ru',
  UA: 'uk',
  IL: 'he',
  IR: 'fa',
  AF: 'fa',
  BD: 'bn',
  CN: 'zh-Hans',
  TW: 'zh-Hant',
  MO: 'zh-Hant',
  VN: 'vi',
  TH: 'th',
  CZ: 'cs',
  SK: 'sk',
  SI: 'sl',
  RO: 'ro',
  MD: 'ro',
  BG: 'bg',
  RS: 'sr',
  ME: 'sr',
  AL: 'sq',
  XK: 'sq',
  GR: 'el',
  CY: 'el',
  DK: 'da',
  NO: 'nb',
  FI: 'fi',
  EE: 'et',
  LV: 'lv',
  LT: 'lt',
  HR: 'hr',
  // Arabic-speaking countries
  EG: 'ar',
  SA: 'ar',
  DZ: 'ar',
  IQ: 'ar',
  MA: 'ar',
  SD: 'ar',
  YE: 'ar',
  SY: 'ar',
  TN: 'ar',
  JO: 'ar',
  LY: 'ar',
  LB: 'ar',
  OM: 'ar',
  KW: 'ar',
  QA: 'ar',
  BH: 'ar',
}

/** The supported UI locale for an ISO country code (CF-IPCountry), or null if
 * that country's language isn't one we translate. */
export function getLocaleFromCountry(
  countryCode: string | null | undefined,
): AcceptedLocale | null {
  if (!countryCode) return null
  const locale = COUNTRY_LOCALE[countryCode.trim().toUpperCase()]
  return locale && isAcceptedLocale(locale) ? locale : null
}

/** The reader's detected country (Cloudflare CF-IPCountry, mirrored into the
 * geo cookie by the proxy) as an ISO-3166 alpha-2 code, for showing their
 * country's flag. Client-only — returns null during SSR or without the cookie. */
export function getClientCountry(): string | null {
  const country = readCookie(GEO_COUNTRY_COOKIE)
  return country ? country.trim().toUpperCase() : null
}

/** Whether the reader explicitly chose a language via the flag picker. Such a
 * choice takes precedence over their detected country for the displayed flag. */
export function hasLocaleOverride(): boolean {
  const override = readCookie(LOCALE_OVERRIDE_COOKIE)
  return !!(override && isAcceptedLocale(override))
}

/** The ISO-3166 country flag the reader picked for an English variant (e.g. "IE"
 * for "English (Ireland)"), or null. Client-only. */
export function getFlagOverride(): string | null {
  const country = readCookie(FLAG_OVERRIDE_COOKIE)
  return country ? country.trim().toUpperCase() : null
}

function getBrowserLocaleFromNavigator(): AcceptedLocale | null {
  if (typeof navigator === 'undefined') return null
  const langs = navigator.languages?.length
    ? navigator.languages
    : [navigator.language]
  for (const code of langs) {
    if (!code) continue
    const supported = toSupportedLocale(code)
    if (supported) return supported
  }
  return null
}

/** Resolve the reader's locale in the browser, re-resolving after hydration to
 * pick up client-only cookie changes (mirrors the server resolveLocale).
 * Priority: a `?lang=` share param (so a shared card opens in the sharer's
 * language) > an explicit language choice (flag picker) > an explicit
 * non-English browser language > the reader's country language (geo cookie) >
 * the server-provided locale. Falls back to the server locale during SSR. */
export function resolveClientLocale(
  serverLocale: AcceptedLocale,
): AcceptedLocale {
  if (typeof window === 'undefined') return serverLocale
  // A shared link carries the sharer's language so the recipient sees the card
  // exactly as it was shared; it wins for as long as the param is in the URL.
  const shared = new URLSearchParams(window.location.search).get('lang')
  if (shared && isAcceptedLocale(shared)) return shared
  const override = readCookie(LOCALE_OVERRIDE_COOKIE)
  if (override && isAcceptedLocale(override)) return override
  const browserLocale = getBrowserLocaleFromNavigator()
  if (browserLocale && browserLocale !== DEFAULT_LOCALE) return browserLocale
  const countryLocale = getLocaleFromCountry(readCookie(GEO_COUNTRY_COOKIE))
  if (countryLocale) return countryLocale
  return browserLocale ?? serverLocale
}
