'use client'

import { useSyncExternalStore } from 'react'

const MOBILE_QUERY = '(max-width: 768px)'
const subscribeMobile = (onChange: () => void) => {
  const mq = window.matchMedia(MOBILE_QUERY)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}
const getMobileSnapshot = () => window.matchMedia(MOBILE_QUERY).matches
const getMobileServerSnapshot = () => false

/** Viewport-only mobile flag, read synchronously from matchMedia: no
 * post-mount state flip (so layout that depends on it doesn't jump on first
 * paint) and a single listener however many components share it. */
export const useIsMobileMedia = (): boolean =>
  useSyncExternalStore(
    subscribeMobile,
    getMobileSnapshot,
    getMobileServerSnapshot,
  )
