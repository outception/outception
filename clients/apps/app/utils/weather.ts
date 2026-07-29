/**
 * Device-region detection: the reader's country from the device locale or
 * timezone. Used to seed the country-tailored default deck and to pick the
 * English-variant flag in the language picker. (This file once also carried
 * the weather card's data layer; the card was removed.)
 */
import { getCalendars, getLocales } from 'expo-localization'

const TZ_COUNTRY: Record<string, string> = {
  'Europe/Dublin': 'IE',
  'Europe/London': 'GB',
  'Europe/Belfast': 'GB',
  'Europe/Paris': 'FR',
  'Europe/Berlin': 'DE',
  'Europe/Madrid': 'ES',
  'Europe/Rome': 'IT',
  'Europe/Amsterdam': 'NL',
  'Europe/Brussels': 'BE',
  'Europe/Lisbon': 'PT',
  'Europe/Vienna': 'AT',
  'Europe/Zurich': 'CH',
  'Europe/Stockholm': 'SE',
  'Europe/Oslo': 'NO',
  'Europe/Copenhagen': 'DK',
  'Europe/Helsinki': 'FI',
  'Europe/Warsaw': 'PL',
  'Europe/Prague': 'CZ',
  'Europe/Athens': 'GR',
  'Europe/Bucharest': 'RO',
  'Europe/Budapest': 'HU',
  'Europe/Kyiv': 'UA',
  'Europe/Moscow': 'RU',
  'America/New_York': 'US',
  'America/Chicago': 'US',
  'America/Denver': 'US',
  'America/Los_Angeles': 'US',
  'America/Toronto': 'CA',
  'America/Vancouver': 'CA',
  'America/Sao_Paulo': 'BR',
  'America/Mexico_City': 'MX',
  'Australia/Sydney': 'AU',
  'Australia/Melbourne': 'AU',
  'Pacific/Auckland': 'NZ',
  'Asia/Tokyo': 'JP',
  'Asia/Seoul': 'KR',
  'Asia/Shanghai': 'CN',
  'Asia/Hong_Kong': 'HK',
  'Asia/Singapore': 'SG',
  'Asia/Kolkata': 'IN',
  'Asia/Dubai': 'AE',
  'Africa/Johannesburg': 'ZA',
  'Africa/Lagos': 'NG',
  'Africa/Cairo': 'EG',
}

/** The device's region (e.g. "IE"), used to tailor the default deck. This is
 * the mobile analogue of the web's IP-country signal.
 *
 * The time zone is preferred over the locale's region because the latter comes
 * from the device's *language* ("English (United States)" is the out-of-box
 * default on most handsets), so an Irish reader would otherwise be told the
 * weather in Washington and shown a US deck. */
const resolveDeviceCountry = (): string | null => {
  try {
    const tz =
      getCalendars()[0]?.timeZone ??
      Intl.DateTimeFormat().resolvedOptions().timeZone
    if (tz && TZ_COUNTRY[tz]) return TZ_COUNTRY[tz]
  } catch {
    // expo-localization unavailable - no confident signal
  }
  // Deliberately no locale-region fallback: `regionCode` comes from the UI
  // language, so it reports US on any factory-default handset. Returning null
  // lets the backend geolocate from the request IP (its CF-IPCountry fallback),
  // which is the same signal the web uses and is right far more often than the
  // language guess.
  return null
}

let cachedCountry: string | null | undefined

export const deviceCountry = (): string | null => {
  // Memoised: this runs on every render of the feed (it feeds a query key) and
  // getCalendars() is a synchronous native call. The device region can't change
  // while the app is running.
  if (cachedCountry !== undefined) return cachedCountry
  cachedCountry = resolveDeviceCountry()
  return cachedCountry
}

/** The device region for *display* purposes (the header flag), where a wrong
 * guess is cosmetic rather than serving the wrong country's news. Falls back to
 * the language region when the time zone isn't recognised. */
export const deviceCountryLoose = (): string | null => {
  const confident = deviceCountry()
  if (confident) return confident
  try {
    for (const locale of getLocales()) {
      if (locale.regionCode) return locale.regionCode.toUpperCase()
    }
  } catch {
    // expo-localization unavailable - no signal at all
  }
  return null
}
