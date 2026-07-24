import {
  type AcceptedLocale,
  getTranslations,
  isAcceptedLocale,
  type Translations,
} from '@outception-com/i18n'
import { cookies, headers } from 'next/headers'
import {
  GEO_COUNTRY_COOKIE,
  LOCALE_OVERRIDE_COOKIE,
  getBrowserLocale,
  getLocaleFromAcceptLanguageHeader,
  getLocaleFromCountry,
} from './shared'

export * from './shared'

/** Server-side locale resolution (for dynamic routes like auth and the
 * dashboard). Priority mirrors the client resolver so a page rendered on the
 * server matches what the reader picked: explicit ?locale > the reader's saved
 * language choice (oc-locale cookie, set by the flag picker) > a non-English
 * browser preference > the reader's country language (Cloudflare CF-IPCountry,
 * or the oc-geo-country cookie the proxy mirrors it into) > English. The landing
 * is force-dynamic so it resolves here on the server; the client resolver
 * (resolveClientLocale) mirrors this priority and re-resolves after hydration to
 * pick up client-only cookie changes (e.g. the flag picker). */
export async function resolveLocale(
  searchParamLocale?: string,
): Promise<AcceptedLocale> {
  if (searchParamLocale && isAcceptedLocale(searchParamLocale)) {
    return searchParamLocale
  }

  const cookieStore = await cookies()
  const override = cookieStore.get(LOCALE_OVERRIDE_COOKIE)?.value
  if (override && isAcceptedLocale(override)) {
    return override
  }

  const headersList = await headers()
  const acceptLanguage = headersList.get('accept-language')

  // An explicit browser preference for a supported non-English language wins.
  const browserLocale = getBrowserLocale(acceptLanguage)
  if (browserLocale && browserLocale !== 'en') {
    return browserLocale
  }

  // Fall back to the reader's country language (CF-IPCountry header, or the
  // cookie the proxy mirrors it into for static routes) before English.
  const countryLocale = getLocaleFromCountry(
    headersList.get('cf-ipcountry') ??
      cookieStore.get(GEO_COUNTRY_COOKIE)?.value,
  )
  if (countryLocale) {
    return countryLocale
  }

  return getLocaleFromAcceptLanguageHeader(acceptLanguage)
}

/** Localized page/tab `<title>` for a server component's metadata, resolved to
 * the reader's locale (see resolveLocale). */
export async function metaTitle(
  key: keyof Translations['meta'],
): Promise<string> {
  return getTranslations(await resolveLocale()).meta[key]
}
