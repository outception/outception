import type { NewsSourceMeta } from '@/utils/news'
import { getLocales } from 'expo-localization'

/** The weather card is a synthetic deck entry (not a scraped source): it shares
 * the source-card shell — accent tab, swipe, unfollow — but renders from the
 * /news/weather proxy instead of a headline feed. Mirrors the web util. */
export const WEATHER_SOURCE_ID = 'weather'

export const WEATHER_SOURCE_META: NewsSourceMeta = {
  id: WEATHER_SOURCE_ID,
  name: 'Weather',
  color: '#38bdf8',
  column: 'weather',
  interval: 900_000,
}

const API_BASE =
  process.env.EXPO_PUBLIC_OUTCEPTION_SERVER_URL ?? 'https://api.outception.com'

export type WeatherLocation = {
  latitude?: number
  longitude?: number
  country?: string
}

export interface WeatherData {
  location: string
  latitude: number
  longitude: number
  timezone: string
  current: {
    temperature: number
    apparentTemperature: number
    weatherCode: number
    windSpeed: number
    humidity: number
    isDay: boolean
  }
  daily: Array<{
    date: string
    weatherCode: number
    tempMax: number
    tempMin: number
  }>
}

/** The device's region (e.g. "IE"), used as the weather location when we have
 * no precise coordinates — the backend resolves a country to its capital. This
 * is the mobile analogue of the web's IP-country fallback (no `expo-location`
 * native module, so there's no precise-coordinate path). */
export const deviceCountry = (): string | null => {
  try {
    for (const locale of getLocales()) {
      if (locale.regionCode) return locale.regionCode.toUpperCase()
    }
  } catch {
    // expo-localization unavailable — no location signal
  }
  return null
}

export const weatherApi = {
  // Hand-rolled fetch: this endpoint isn't in the generated client (like
  // default-deck). Precise coordinates win; otherwise the country is sent and
  // the backend resolves that country's capital.
  forecast: async (loc: WeatherLocation): Promise<WeatherData> => {
    const params = new URLSearchParams()
    if (loc.latitude != null && loc.longitude != null) {
      params.set('latitude', String(loc.latitude))
      params.set('longitude', String(loc.longitude))
    } else if (loc.country) {
      params.set('country', loc.country)
    }
    const res = await fetch(`${API_BASE}/v1/news/weather?${params.toString()}`)
    if (!res.ok) throw new Error(`weather ${res.status}`)
    return (await res.json()) as WeatherData
  },
}

// WMO weather-interpretation codes → a short label key. Grouped per the
// Open-Meteo docs (drizzle/rain/snow families collapse to one entry).
const WMO_LABEL: Record<number, string> = {
  0: 'clear',
  1: 'mainlyClear',
  2: 'partlyCloudy',
  3: 'overcast',
  45: 'fog',
  48: 'fog',
  51: 'drizzle',
  53: 'drizzle',
  55: 'drizzle',
  56: 'drizzle',
  57: 'drizzle',
  61: 'rain',
  63: 'rain',
  65: 'rain',
  66: 'rain',
  67: 'rain',
  71: 'snow',
  73: 'snow',
  75: 'snow',
  77: 'snow',
  80: 'showers',
  81: 'showers',
  82: 'showers',
  85: 'snow',
  86: 'snow',
  95: 'thunderstorm',
  96: 'thunderstorm',
  99: 'thunderstorm',
}

/** The i18n key suffix under `news.weather.codes.*` for a WMO code. */
export const weatherLabelKey = (code: number): string =>
  WMO_LABEL[code] ?? 'unknown'

/** A weather glyph for a WMO code, dimmed to the night variant after dark. */
export const weatherGlyph = (code: number, isDay: boolean): string => {
  if (code === 0 || code === 1) return isDay ? '☀️' : '🌙'
  if (code === 2) return isDay ? '⛅' : '☁️'
  if (code === 3) return '☁️'
  if (code === 45 || code === 48) return '🌫️'
  if (code >= 51 && code <= 57) return '🌦️'
  if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82)) return '🌧️'
  if ((code >= 71 && code <= 77) || code === 85 || code === 86) return '🌨️'
  if (code >= 95) return '⛈️'
  return '🌡️'
}

export const formatTemp = (celsius: number): string => `${Math.round(celsius)}°`
