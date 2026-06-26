'use client'

import {
  type AcceptedLocale,
  DEFAULT_LOCALE,
  useTranslations,
} from '@outception-com/i18n'
import { createContext, useContext, type ReactNode } from 'react'

const LocaleContext = createContext<AcceptedLocale>(DEFAULT_LOCALE)

/** Hands the server-resolved locale (see `resolveLocale`) to client
 * components. Mounted once at the root layout so anything under it can call
 * `useT()`. */
export const LocaleProvider = ({
  locale,
  children,
}: {
  locale: AcceptedLocale
  children: ReactNode
}) => <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>

export const useLocale = () => useContext(LocaleContext)

/** The translate function bound to the active locale: `const t = useT()`. */
export const useT = () => useTranslations(useLocale())
