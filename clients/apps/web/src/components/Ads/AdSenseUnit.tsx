'use client'

import {
  COOKIE_CONSENT_EVENT,
  cookieConsentGiven,
} from '@/components/Privacy/CookieConsent'
import { CONFIG } from '@/utils/config'
import { useEffect, useRef, useState } from 'react'

declare global {
  interface Window {
    adsbygoogle?: unknown[]
  }
}

/**
 * A single AdSense display unit. Renders the AdSense-mandated `<ins
 * class="adsbygoogle">` element (a third-party contract — this is the one place
 * a raw className element is required over Box) and pushes it to the ad queue
 * once on mount. Renders nothing until a publisher id + slot are configured, so
 * the wall works before AdSense approval.
 */
export const AdSenseUnit = ({
  slot,
  className,
}: {
  slot?: string
  className?: string
}) => {
  const client = CONFIG.ADSENSE_CLIENT
  const pushed = useRef(false)
  // A reader who declined must not have ad requests fired for them. Consent
  // mode already downgrades ads to non-personalised for undecided EEA readers;
  // an explicit "no" stops the request altogether.
  const [declined, setDeclined] = useState(false)

  useEffect(() => {
    const sync = () => setDeclined(cookieConsentGiven() === 'no')
    sync()
    window.addEventListener(COOKIE_CONSENT_EVENT, sync)
    return () => window.removeEventListener(COOKIE_CONSENT_EVENT, sync)
  }, [])

  useEffect(() => {
    if (!client || !slot || declined || pushed.current) return
    pushed.current = true
    try {
      ;(window.adsbygoogle = window.adsbygoogle || []).push({})
    } catch {
      // AdSense not loaded yet / already filled — safe to ignore.
    }
  }, [client, slot, declined])

  if (!client || !slot || declined) return null

  return (
    <ins
      className={`adsbygoogle ${className ?? ''}`.trim()}
      style={{ display: 'block' }}
      data-ad-client={client}
      data-ad-slot={slot}
      data-ad-format="auto"
      data-full-width-responsive="true"
    />
  )
}
