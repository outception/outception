'use client'

import { useEffect, useState } from 'react'

/** A clock that ticks every `intervalMs`, so freshness reads re-derive as
 * time passes without calling the clock during render. */
export const useNow = (intervalMs = 60_000): number => {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(timer)
  }, [intervalMs])
  return now
}
