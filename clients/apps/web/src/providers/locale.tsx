'use client'

import { subscribeLocaleOverride } from '@/utils/i18n/localeOverride'
import { resolveClientLocale } from '@/utils/i18n/shared'
import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  getLocaleDir,
  type LocaleMessages,
  getTranslationsVersion,
  loadTranslations,
  seedTranslations,
  subscribeTranslations,
  useTranslations,
} from '@outception-com/i18n'
import {
  createContext,
  useContext,
  useEffect,
  useReducer,
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
  messages,
  children,
}: {
  locale: AcceptedLocale
  /** The server-resolved locale's strings, so the first paint is already in
   * the reader's language. Null for English, or when the chunk failed to load
   * server-side, in which case the client lazy-loads it as before. */
  messages?: LocaleMessages | null
  children: ReactNode
}) => {
  // During render, before any child reads `useT`: this module instance is the
  // one the first (server) paint of every client component reads, and a chunk
  // loaded in the Server Component graph never reaches it.
  if (messages) seedTranslations(serverLocale, messages)
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
  // Locales load lazily (per-locale chunks): kick off the active locale's
  // chunk and re-render the tree when any chunk lands so `useT` swaps from
  // the English fallback to the real strings.
  const [, bumpTranslations] = useReducer((n: number) => n + 1, 0)
  useEffect(() => subscribeTranslations(bumpTranslations), [])
  useEffect(() => {
    void loadTranslations(locale)
  }, [locale])
  return (
    <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>
  )
}

export const useLocale = () => useContext(LocaleContext)

/** The translate function bound to the active locale: `const t = useT()`. */
export const useT = () => {
  // Subscribed per consumer, not just in the provider: non-English strings
  // load lazily, and a provider-only re-render leaves memoised children (and
  // any component with no state of its own) showing English until something
  // else re-renders them - a half-translated page. Lives here rather than in
  // the i18n package because that module is imported by Server Components.
  const version = useSyncExternalStore(
    subscribeTranslations,
    getTranslationsVersion,
    getTranslationsVersion,
  )
  return useTranslations(useLocale(), version)
}
