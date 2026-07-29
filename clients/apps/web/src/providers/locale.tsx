'use client'

import { subscribeLocaleOverride } from '@/utils/i18n/localeOverride'
import { resolveClientLocale } from '@/utils/i18n/shared'
import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  getLocaleDir,
  useTranslations,
} from '@outception-com/i18n'
import {
  createContext,
  useContext,
  useEffect,
  useSyncExternalStore,
  type ReactNode,
} from 'react'

const LocaleContext = createContext<AcceptedLocale>(DEFAULT_LOCALE)

/** Hands the active locale to client components. The server passes its
 * resolved locale (see `resolveLocale`); on the force-static landing shell
 * that's always the default, so after hydration the client re-resolves from
 * the browser language + the geo cookie (see `resolveClientLocale`). Using
 * useSyncExternalStore keeps the first client render matching the server
 * (no hydration mismatch), then swaps to the client-resolved locale. */
export const LocaleProvider = ({
  locale: serverLocale,
  children,
}: {
  locale: AcceptedLocale
  children: ReactNode
}) => {
  // Re-resolve whenever the reader picks a language (the override store
  // signals a change); resolveClientLocale reads the current cookies.
  const locale = useSyncExternalStore(
    subscribeLocaleOverride,
    () => resolveClientLocale(serverLocale),
    () => serverLocale,
  )
  // Keep <html lang> and <html dir> in step with the client-resolved locale
  // (the static shell is baked as the server default) for assistive tech, SEO,
  // and right-to-left mirroring when the reader switches to Arabic/Hebrew/etc.
  useEffect(() => {
    document.documentElement.lang = locale
    document.documentElement.dir = getLocaleDir(locale)
  }, [locale])
  return (
    <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>
  )
}

export const useLocale = () => useContext(LocaleContext)

/** The translate function bound to the active locale: `const t = useT()`. */
export const useT = () => useTranslations(useLocale())
