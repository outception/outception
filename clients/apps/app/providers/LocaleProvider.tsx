import { ensureIntlLocaleData } from '@/polyfills/intl'
import {
  getLocaleSettled,
  getLocaleSnapshot,
  subscribeLocale,
} from '@/utils/locale'
import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  getTranslationsVersion,
  isRtlLocale,
  loadTranslations,
  subscribeTranslations,
  type TranslateFn,
  useTranslations,
} from '@outception-com/i18n'
import * as Updates from 'expo-updates'
import {
  createContext,
  useContext,
  useEffect,
  useReducer,
  useSyncExternalStore,
} from 'react'
import type { PropsWithChildren } from 'react'
import { AppState, I18nManager } from 'react-native'

const LocaleContext = createContext<AcceptedLocale>(DEFAULT_LOCALE)

/** Drive React Native's global layout direction from the active locale. RN only
 * applies an RTL flip after a native reload, so when the direction changes we
 * flip `I18nManager` and reload (a no-op guard prevents a loop; reloadAsync is
 * unavailable in Expo Go/dev, so it's caught). This mirrors the web `<html dir>`. */
// One reload per process. `forceRTL` persists a NATIVE flag, but the JS-side
// `I18nManager.isRTL` is captured at bridge init - if it still reports the old
// value after reloadAsync, the effect fires again and the app reloads forever,
// leaving it unlaunchable for every ar/he/fa/ur reader. The guard below is the
// very value that may not have updated, so it can't be the only one.
let directionFlipAttempted = false

const useAppDirection = (locale: AcceptedLocale, settled: boolean): void => {
  useEffect(() => {
    // Never act on a provisional locale. The splash releases on whichever of
    // the stored-language read and the 1.5s budget lands first, so on a slow
    // device the tree renders with the DEVICE language before the reader's
    // real choice is known. Flipping on that value set the native RTL flag
    // the wrong way and relaunched the app; the relaunch then read the real
    // language, disagreed again, and relaunched once more - unusable for an
    // ar/he/fa/ur reader whose storage is consistently slow. The module guard
    // below cannot help, because each relaunch is a fresh JS context.
    if (!settled) return
    const shouldRtl = isRtlLocale(locale)
    if (I18nManager.isRTL === shouldRtl) return
    if (directionFlipAttempted) return
    directionFlipAttempted = true
    I18nManager.allowRTL(shouldRtl)
    I18nManager.forceRTL(shouldRtl)
    void Updates.reloadAsync().catch(() => {
      // Dev/Expo Go: the direction applies on the next manual reload.
    })
  }, [locale, settled])
}

/** Provides the reader's resolved UI locale (their explicit choice, else the
 * device language) to the tree. Backed by an external store so a language
 * change re-renders every consumer of `useT`. */
export const LocaleProvider = ({ children }: PropsWithChildren) => {
  const locale = useSyncExternalStore(
    subscribeLocale,
    getLocaleSnapshot,
    getLocaleSnapshot,
  )
  // Synchronous and before any child renders: consumers build their Intl
  // formatters for this locale during render, and the data has to be
  // registered with the polyfills by then (see polyfills/intl).
  ensureIntlLocaleData(locale)
  // Subscribed, not read once: the store notifies on settle even when the
  // resolved locale is unchanged (the reader follows the device language), and
  // the direction flip has to wait for that.
  const settled = useSyncExternalStore(
    subscribeLocale,
    getLocaleSettled,
    getLocaleSettled,
  )
  useAppDirection(locale, settled)
  // Locale strings evaluate lazily; load the active locale and re-render
  // consumers when its strings land (English serves in the interim).
  const [, bumpTranslations] = useReducer((n: number) => n + 1, 0)
  useEffect(() => subscribeTranslations(bumpTranslations), [])
  useEffect(() => {
    void loadTranslations(locale)
    // A chunk that failed to download (flaky cold-launch network) otherwise
    // strands the session in English: retry whenever the app foregrounds.
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') void loadTranslations(locale)
    })
    return () => sub.remove()
  }, [locale])
  return (
    <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>
  )
}

export const useLocale = (): AcceptedLocale => useContext(LocaleContext)

export const useT = (): TranslateFn => {
  // Subscribed per consumer, not just in the provider: non-English strings
  // load lazily, and a provider-only re-render leaves memoised children (and
  // any component with no state of its own - the card set tabs, settings rows)
  // showing English until something else re-renders them, while cards that
  // re-render when their data lands switch: a half-translated app. Lives
  // here rather than in the i18n package, which the web imports from React
  // Server Components where a client-only hook fails the build.
  const version = useSyncExternalStore(
    subscribeTranslations,
    getTranslationsVersion,
    getTranslationsVersion,
  )
  return useTranslations(useLocale(), version)
}
