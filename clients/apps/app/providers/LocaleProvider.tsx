import { getLocaleSnapshot, subscribeLocale } from '@/utils/locale'
import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
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
import { I18nManager } from 'react-native'

const LocaleContext = createContext<AcceptedLocale>(DEFAULT_LOCALE)

/** Drive React Native's global layout direction from the active locale. RN only
 * applies an RTL flip after a native reload, so when the direction changes we
 * flip `I18nManager` and reload (a no-op guard prevents a loop; reloadAsync is
 * unavailable in Expo Go/dev, so it's caught). This mirrors the web `<html dir>`. */
// One reload per process. `forceRTL` persists a NATIVE flag, but the JS-side
// `I18nManager.isRTL` is captured at bridge init — if it still reports the old
// value after reloadAsync, the effect fires again and the app reloads forever,
// leaving it unlaunchable for every ar/he/fa/ur reader. The guard below is the
// very value that may not have updated, so it can't be the only one.
let directionFlipAttempted = false

const useAppDirection = (locale: AcceptedLocale): void => {
  useEffect(() => {
    const shouldRtl = isRtlLocale(locale)
    if (I18nManager.isRTL === shouldRtl) return
    if (directionFlipAttempted) return
    directionFlipAttempted = true
    I18nManager.allowRTL(shouldRtl)
    I18nManager.forceRTL(shouldRtl)
    void Updates.reloadAsync().catch(() => {
      // Dev/Expo Go: the direction applies on the next manual reload.
    })
  }, [locale])
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
  useAppDirection(locale)
  // Locale strings evaluate lazily; load the active locale and re-render
  // consumers when its strings land (English serves in the interim).
  const [, bumpTranslations] = useReducer((n: number) => n + 1, 0)
  useEffect(() => subscribeTranslations(bumpTranslations), [])
  useEffect(() => {
    void loadTranslations(locale)
  }, [locale])
  return (
    <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>
  )
}

export const useLocale = (): AcceptedLocale => useContext(LocaleContext)

export const useT = (): TranslateFn => useTranslations(useLocale())
