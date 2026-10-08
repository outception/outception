'use client'

import { holds, usePrefersReducedMotion } from '@/utils/motion'
import { glyphsAt, isSettled, planFlap } from '@outception-com/news-core'
import { useEffect, useRef, useState } from 'react'

/**
 * A short label that flips from its old text to its new one, column by
 * column, like a departures board. For kickers and counters only, never
 * headlines. The plan comes from news-core; this component only runs it on
 * the browser's frame clock, under an animation hold, and shows the final
 * text at once under reduced motion or on a hidden tab.
 */
export const SplitFlap = ({
  text,
  owner,
  className,
}: {
  text: string
  /** The hold's owner, usually the card id. */
  owner: string
  className?: string
}) => {
  const reduced = usePrefersReducedMotion()
  const [shown, setShown] = useState(text)
  const previous = useRef(text)

  useEffect(() => {
    const from = previous.current
    previous.current = text
    if (from === text) return
    if (reduced || (!holds.shouldAnimate() && !holds.shouldAnimate(owner))) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- no animation: land on the new text
      setShown(text)
      return
    }
    const plan = planFlap(from, text)
    const release = holds.take(owner)
    const started = performance.now()
    let frame = 0
    const tick = () => {
      const elapsed = performance.now() - started
      setShown(glyphsAt(plan, elapsed))
      if (isSettled(plan, elapsed)) {
        release()
        return
      }
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(frame)
      release()
      setShown(text)
    }
  }, [text, owner, reduced])

  return (
    <span className={className} aria-label={text} data-testid="split-flap">
      <span aria-hidden>{shown}</span>
    </span>
  )
}
