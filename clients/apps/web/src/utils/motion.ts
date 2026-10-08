'use client'

import { createHoldRegistry } from '@outception-com/news-core'
import { useEffect, useSyncExternalStore } from 'react'

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)'

const subscribeReduced = (onChange: () => void) => {
  const mq = window.matchMedia(REDUCED_QUERY)
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}
const getReduced = () => window.matchMedia(REDUCED_QUERY).matches
const getReducedServer = () => false

/** The reader's reduced-motion setting, read synchronously. */
export const usePrefersReducedMotion = (): boolean =>
  useSyncExternalStore(subscribeReduced, getReduced, getReducedServer)

/** The one hold registry: flaps, tickers and auto-play take a hold while
 * they want to animate; a hidden tab or reduced motion stops them all. */
export const holds = createHoldRegistry()

/** Wire the page's visibility and the motion setting into the registry.
 * Mount once, in the layout. */
export const useHoldsEnvironment = (): void => {
  const reduced = usePrefersReducedMotion()
  useEffect(() => {
    holds.setReducedMotion(reduced)
  }, [reduced])
  useEffect(() => {
    const read = () => holds.setVisible(document.visibilityState !== 'hidden')
    read()
    document.addEventListener('visibilitychange', read)
    return () => document.removeEventListener('visibilitychange', read)
  }, [])
}
