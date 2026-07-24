'use client'

import type { AcceptedLocale } from '@outception-com/i18n'
import { FLAG_OVERRIDE_COOKIE, LOCALE_OVERRIDE_COOKIE } from './shared'

// A tiny external store so the flag picker can change the UI language and have
// the LocaleProvider re-render. The value itself lives in the oc-locale cookie
// (read by resolveClientLocale); this store only signals a change.
const listeners = new Set<() => void>()

export const subscribeLocaleOverride = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

/** Persist the reader's explicit language choice (a year) and notify the
 * provider to re-resolve. `flagCountry` (e.g. "IE" for "English (Ireland)")
 * remembers which flag to show for languages offered under several country
 * flags; passing none clears any previous flag choice. */
export const setLocaleOverride = (
  locale: AcceptedLocale,
  flagCountry?: string,
): void => {
  try {
    document.cookie = `${LOCALE_OVERRIDE_COOKIE}=${locale};path=/;max-age=31536000;samesite=lax`
    document.cookie = flagCountry
      ? `${FLAG_OVERRIDE_COOKIE}=${flagCountry};path=/;max-age=31536000;samesite=lax`
      : `${FLAG_OVERRIDE_COOKIE}=;path=/;max-age=0;samesite=lax`
  } catch {
    // cookies disabled — the choice just won't persist
  }
  for (const listener of listeners) listener()
}
