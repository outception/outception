import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  toSupportedLocale as sharedToSupportedLocale,
} from '@outception-com/i18n'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { getLocales } from 'expo-localization'

const SUPPORTED = SUPPORTED_LOCALES as readonly string[]
const OVERRIDE_KEY = 'oc-locale'

/** Reduce a BCP-47 code to a supported UI locale. Re-exported from the shared
 * i18n config so the app and the web resolve device and browser tags
 * identically - the two copies had drifted into silently dropping every
 * Chinese and Filipino tag. */
export const toSupportedLocale = (code: string): AcceptedLocale | null =>
  sharedToSupportedLocale(code) as AcceptedLocale | null

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
    // expo-localization unavailable - fall through to the default
  }
  return DEFAULT_LOCALE
}

// The reader's explicit language choice (the picker), persisted in
// AsyncStorage and exposed as an external store so the LocaleProvider
// re-renders when it changes. Null means "follow the device language".
let override: AcceptedLocale | null = null
let hydration: Promise<void> | null = null
// An explicit choice made while the storage read is still in flight wins:
// without this a slow read resolving AFTER the reader picked (or a ?lang deep
// link applied) a language flipped the UI back to the stale stored value
// while storage already held the new one.
let overrideSettled = false
const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

const hydrate = (): Promise<void> => {
  if (hydration) return hydration
  hydration = AsyncStorage.getItem(OVERRIDE_KEY)
    .then((value) => {
      if (overrideSettled) return
      overrideSettled = true
      if (value && SUPPORTED.includes(value)) {
        override = value as AcceptedLocale
      }
    })
    .catch(() => {})
    // Emit on SETTLE, not only when a stored value was found. Consumers that
    // read the locale alone see no change when the reader follows the device
    // language, but the RTL flip below must know the difference between "the
    // device language, provisionally" and "this is really their language" -
    // acting on the provisional value flipped the native RTL flag and
    // relaunched the app, repeatedly.
    .finally(emit)
  return hydration
}

/** Resolves once the reader's stored language choice has been read, so
 * `getLocaleSnapshot` returns their real locale rather than the device's.
 * Never rejects (a failed read leaves the device language in place). */
export const whenLocaleHydrated = (): Promise<void> => hydrate()

export const subscribeLocale = (listener: () => void): (() => void) => {
  void hydrate()
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getLocaleSnapshot = (): AcceptedLocale =>
  override ?? deviceLocale()

/** Whether the stored-language read has finished. Until it has,
 * `getLocaleSnapshot` is the DEVICE language standing in for a choice we have
 * not read yet, which is fine to render and not fine to act on irreversibly
 * (see useAppDirection). Notified through `subscribeLocale`. */
export const getLocaleSettled = (): boolean => overrideSettled

// The country flag the reader picked alongside an English variant (e.g. "IE"
// for "English (Ireland)"), so the picker keeps showing their flag even though
// the content locale is plain `en`. Mirrors the web `oc-flag` cookie.
const FLAG_KEY = 'oc-flag'
let flagOverride: string | null = null
let flagHydrated = false
// Same race, same guard as the locale override above: an explicit pick made
// while the storage read is still in flight must win. Without it, tapping
// "English (Ireland)" during a slow cold start showed the flag jump back to
// the previously stored country while storage already held the new one.
let flagSettled = false
const flagListeners = new Set<() => void>()
const emitFlag = () => {
  for (const listener of flagListeners) listener()
}

const hydrateFlag = () => {
  if (flagHydrated) return
  flagHydrated = true
  AsyncStorage.getItem(FLAG_KEY)
    .then((value) => {
      if (flagSettled) return
      flagSettled = true
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
  overrideSettled = true
  override = locale
  AsyncStorage.setItem(OVERRIDE_KEY, locale).catch(() => {})
  emit()
  flagSettled = true
  flagOverride = flagCountry ? flagCountry.toUpperCase() : null
  if (flagCountry)
    AsyncStorage.setItem(FLAG_KEY, flagOverride as string).catch(() => {})
  else AsyncStorage.removeItem(FLAG_KEY).catch(() => {})
  emitFlag()
}
