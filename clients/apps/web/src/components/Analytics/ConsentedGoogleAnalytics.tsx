'use client'

import {
  COOKIE_CONSENT_EVENT,
  cookieConsentGiven,
} from '@/components/Privacy/CookieConsent'
import { CONFIG } from '@/utils/config'
import { GoogleAnalytics } from '@next/third-parties/google'
import { runWhenIdle } from '@/utils/idle'
import { useEffect, useState } from 'react'

function updateGoogleConsent(granted: boolean) {
  const value = granted ? 'granted' : 'denied'
  const w = window as unknown as { dataLayer?: unknown[] }
  w.dataLayer = w.dataLayer || []
  // gtag.js only processes `arguments` objects pushed onto the dataLayer —
  // pushing a plain array silently drops the consent command.
  function gtag(..._args: unknown[]) {
    // eslint-disable-next-line prefer-rest-params
    w.dataLayer!.push(arguments)
  }
  gtag('consent', 'update', {
    analytics_storage: value,
  })
}

/**
 * Google Analytics with Consent Mode v2. The tag loads for every reader, but
 * GoogleConsentDefaults boots it with storage denied in the cookie-banner
 * regions — so before consent it only sends cookieless pings (which feed
 * Google's conversion modelling), exactly mirroring PostHog's
 * memory-persistence mode so the two count comparable traffic. Accepting the
 * banner or the preferences modal flips consent to granted; declining pins it
 * denied. Outside the banner regions the defaults are granted and readers are
 * measured normally.
 */
export function ConsentedGoogleAnalytics() {
  // Load the tag once the main thread idles: analytics never competes with
  // the wall's first paint for bandwidth or parse time.
  const [ready, setReady] = useState(false)
  useEffect(() => runWhenIdle(() => setReady(true)), [])
  useEffect(() => {
    const sync = () => {
      const consent = cookieConsentGiven()
      if (consent === 'yes') {
        updateGoogleConsent(true)
      } else if (consent === 'no') {
        updateGoogleConsent(false)
      }
      // 'undecided' keeps the region-scoped defaults from GoogleConsentDefaults
    }
    sync()
    window.addEventListener(COOKIE_CONSENT_EVENT, sync)
    // Cross-tab: another tab accepting/declining updates localStorage.
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(COOKIE_CONSENT_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  if (!CONFIG.GOOGLE_ANALYTICS_ID || !ready) {
    return null
  }
  return <GoogleAnalytics gaId={CONFIG.GOOGLE_ANALYTICS_ID} />
}
