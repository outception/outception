// app/banner.js
'use client'
import { EU_COUNTRY_CODES } from '@/components/Privacy/countries'
import { CONSENT_COOKIE, COOKIE_MAX_AGE } from '@/experiments/constants'
import { usePostHog } from '@/hooks/posthog'
import { useT } from '@/providers/locale'
import { useSearchParams } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import { InlineModal } from '@outception-com/orbit'
import { useModal } from '../Modal/useModal'
import { CookiePreferencesModal } from './CookiePreferencesModal'

export function cookieConsentGiven() {
  if (typeof window === 'undefined' || typeof localStorage === 'undefined') {
    return 'undecided'
  }

  if (!localStorage.getItem('cookie_consent')) {
    return 'undecided'
  }

  return localStorage.getItem('cookie_consent')
}

/** Persist the reader's choice. localStorage is what the client reads; the
 * cookie mirror is for the proxy, which only sets the persistent distinct id
 * cookie once this says yes. */
export function writeCookieConsent(value: 'yes' | 'no') {
  localStorage.setItem('cookie_consent', value)
  document.cookie = `${CONSENT_COOKIE}=${value}; path=/; max-age=${COOKIE_MAX_AGE}; samesite=lax`
}

// Broadcast so same-tab listeners (e.g. the consent-gated Google Analytics tag)
// react immediately when the reader accepts/declines — `storage` events don't
// fire in the tab that made the change.
export const COOKIE_CONSENT_EVENT = 'outception:cookie-consent'
function announceConsent() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(COOKIE_CONSENT_EVENT))
  }
}

export function CookieConsent({ countryCode }: { countryCode: string | null }) {
  const isEU = countryCode ? EU_COUNTRY_CODES.includes(countryCode) : false
  const [consentGiven, setConsentGiven] = useState<string | null>('')
  const {
    isShown: preferencesOpen,
    show: showPreferences,
    hide: hidePreferences,
  } = useModal()
  const { setPersistence } = usePostHog()
  const t = useT()
  const searchParams = useSearchParams()

  let doNotTrackParameter = searchParams.get('do_not_track')

  // The do_not_track parameter can be passed in the query params or in the return_to parameter
  if (!doNotTrackParameter) {
    const returnTo = searchParams.get('return_to')
    if (returnTo) {
      try {
        const returnToUrl = new URL(returnTo, window.location.origin)
        doNotTrackParameter = returnToUrl.searchParams.get('do_not_track')
      } catch {
        // No parameter found, nothing to do
      }
    }
  }

  const declineCookies = useCallback(() => {
    writeCookieConsent('no')
    setConsentGiven('no')
    announceConsent()
  }, [setConsentGiven])

  useEffect(() => {
    const currentConsent = cookieConsentGiven()

    if (doNotTrackParameter && currentConsent === 'undecided') {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- client-only localStorage read to avoid hydration mismatch
      declineCookies()
    } else {
      setConsentGiven(currentConsent)
    }
  }, [declineCookies, doNotTrackParameter])

  // Saving from the preferences modal writes consent and announces it, but this
  // banner holds its own copy — without re-syncing it stays on screen
  // contradicting the choice the reader just made.
  useEffect(() => {
    const sync = () => setConsentGiven(cookieConsentGiven())
    window.addEventListener(COOKIE_CONSENT_EVENT, sync)
    return () => window.removeEventListener(COOKIE_CONSENT_EVENT, sync)
  }, [])

  useEffect(() => {
    if (consentGiven !== '') {
      setPersistence(consentGiven === 'yes' ? 'localStorage' : 'memory')
    }
  }, [consentGiven, setPersistence])

  const handleAcceptCookies = () => {
    writeCookieConsent('yes')
    setConsentGiven('yes')
    announceConsent()
  }

  const handleDeclineCookies = () => {
    declineCookies()
  }

  if (!isEU || doNotTrackParameter) {
    return null
  }

  return (
    <>
      {consentGiven === 'undecided' && (
        <div className="shadow-3xl dark:bg-outception-950 dark:border-outception-700 dark:text-outception-500 fixed right-8 bottom-8 left-8 z-50 flex flex-col gap-y-4 rounded-2xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-500 md:left-auto md:max-w-96">
          {/* Analytics-only consent: the site runs no advertising, so the
              notice covers exactly what runs. Translated, because this banner
              is shown ONLY to EU/EEA/UK readers. */}
          <p>{t('cookies.body')}</p>
          <div className="flex flex-row items-center gap-x-4">
            <button
              className="cursor-pointer text-blue-500 transition-colors hover:text-blue-600 dark:text-white dark:hover:text-gray-200"
              onClick={handleAcceptCookies}
              type="button"
            >
              {t('cookies.accept')}
            </button>
            <button
              className="cursor-pointer text-gray-500 transition-colors hover:text-gray-600 dark:hover:text-gray-600"
              onClick={handleDeclineCookies}
              type="button"
            >
              {t('cookies.decline')}
            </button>
            <button
              className="cursor-pointer transition-colors hover:text-gray-400 dark:hover:text-gray-400"
              onClick={showPreferences}
              type="button"
            >
              {t('cookies.managePreferences')}
            </button>
          </div>
        </div>
      )}
      <InlineModal
        isShown={preferencesOpen}
        hide={hidePreferences}
        modalContent={<CookiePreferencesModal hide={hidePreferences} />}
      />
    </>
  )
}
