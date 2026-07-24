import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
} from '@outception-com/i18n'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { getLocales } from 'expo-localization'

const SUPPORTED = SUPPORTED_LOCALES as readonly string[]
const OVERRIDE_KEY = 'oc-locale'

/** Reduce a BCP-47 code to a supported UI locale: an exact match (e.g. `pt-PT`)
 * as-is, else the bare primary language if we support it (`de-DE` → `de`), else
 * null. */
export function toSupportedLocale(code: string): AcceptedLocale | null {
  if (SUPPORTED.includes(code)) return code as AcceptedLocale
  const primary = code.split('-')[0]
  if (SUPPORTED.includes(primary)) return primary as AcceptedLocale
  return null
}

/** The reader's device language, normalized to a supported UI locale (falls
 * back to English when the device language isn't one we translate). */
export function deviceLocale(): AcceptedLocale {
  try {
    for (const locale of getLocales()) {
      const supported =
        toSupportedLocale(locale.languageTag) ??
        (locale.languageCode ? toSupportedLocale(locale.languageCode) : null)
      if (supported) return supported
    }
  } catch {
    // expo-localization unavailable — fall through to the default
  }
  return DEFAULT_LOCALE
}

// The reader's explicit language choice (the picker), persisted in
// AsyncStorage and exposed as an external store so the LocaleProvider
// re-renders when it changes. Null means "follow the device language".
let override: AcceptedLocale | null = null
let hydrated = false
const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

const hydrate = () => {
  if (hydrated) return
  hydrated = true
  AsyncStorage.getItem(OVERRIDE_KEY)
    .then((value) => {
      if (value && SUPPORTED.includes(value)) {
        override = value as AcceptedLocale
        emit()
      }
    })
    .catch(() => {})
}

export const subscribeLocale = (listener: () => void): (() => void) => {
  hydrate()
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getLocaleSnapshot = (): AcceptedLocale =>
  override ?? deviceLocale()

// The country flag the reader picked alongside an English variant (e.g. "IE"
// for "English (Ireland)"), so the picker keeps showing their flag even though
// the content locale is plain `en`. Mirrors the web `oc-flag` cookie.
const FLAG_KEY = 'oc-flag'
let flagOverride: string | null = null
let flagHydrated = false
const flagListeners = new Set<() => void>()
const emitFlag = () => {
  for (const listener of flagListeners) listener()
}

const hydrateFlag = () => {
  if (flagHydrated) return
  flagHydrated = true
  AsyncStorage.getItem(FLAG_KEY)
    .then((value) => {
      if (value) {
        flagOverride = value.toUpperCase()
        emitFlag()
      }
    })
    .catch(() => {})
}

export const subscribeFlag = (listener: () => void): (() => void) => {
  hydrateFlag()
  flagListeners.add(listener)
  return () => {
    flagListeners.delete(listener)
  }
}

/** The country flag chosen for an English variant (e.g. "IE"), or null. */
export const getFlagSnapshot = (): string | null => flagOverride

/** Persist the reader's explicit language choice and notify subscribers.
 * `flagCountry` (e.g. "IE") remembers which flag to show for languages offered
 * under several country flags; passing none clears any previous flag choice. */
export const setLocaleOverride = (
  locale: AcceptedLocale,
  flagCountry?: string,
): void => {
  override = locale
  AsyncStorage.setItem(OVERRIDE_KEY, locale).catch(() => {})
  emit()
  flagOverride = flagCountry ? flagCountry.toUpperCase() : null
  if (flagCountry)
    AsyncStorage.setItem(FLAG_KEY, flagOverride as string).catch(() => {})
  else AsyncStorage.removeItem(FLAG_KEY).catch(() => {})
  emitFlag()
}
