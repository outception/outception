'use client'

import { CONFIG } from '@/utils/config'
import { useEffect, useRef } from 'react'

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

  useEffect(() => {
    if (!client || !slot || pushed.current) return
    pushed.current = true
    try {
      ;(window.adsbygoogle = window.adsbygoogle || []).push({})
    } catch {
      // AdSense not loaded yet / already filled — safe to ignore.
    }
  }, [client, slot])

  if (!client || !slot) return null

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
