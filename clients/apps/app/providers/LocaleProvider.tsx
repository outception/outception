import { getLocaleSnapshot, subscribeLocale } from '@/utils/locale'
import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  isRtlLocale,
  type TranslateFn,
  useTranslations,
} from '@outception-com/i18n'
import * as Updates from 'expo-updates'
import {
  createContext,
  useContext,
  useEffect,
  useSyncExternalStore,
} from 'react'
import type { PropsWithChildren } from 'react'
import { I18nManager } from 'react-native'

const LocaleContext = createContext<AcceptedLocale>(DEFAULT_LOCALE)

/** Drive React Native's global layout direction from the active locale. RN only
 * applies an RTL flip after a native reload, so when the direction changes we
 * flip `I18nManager` and reload (a no-op guard prevents a loop; reloadAsync is
 * unavailable in Expo Go/dev, so it's caught). This mirrors the web `<html dir>`. */
const useAppDirection = (locale: AcceptedLocale): void => {
  useEffect(() => {
    const shouldRtl = isRtlLocale(locale)
    if (I18nManager.isRTL === shouldRtl) return
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
  return (
    <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>
  )
}

export const useLocale = (): AcceptedLocale => useContext(LocaleContext)

export const useT = (): TranslateFn => useTranslations(useLocale())
