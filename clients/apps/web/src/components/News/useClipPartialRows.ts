'use client'

import { useEffect, type RefObject } from 'react'

/**
 * The deck card doesn't scroll, so its headline list is clipped by overflow —
 * which can slice the last visible row in half. This hides any row whose bottom
 * falls past the card's visible area so the clip always lands on whole rows: a
 * row is shown only if it fits completely, otherwise it (and everything below)
 * is hidden. Re-runs on resize and whenever the list's contents change.
 */
export const useClipPartialRows = (
  containerRef: RefObject<HTMLElement | null>,
) => {
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const apply = () => {
      const list = container.firstElementChild
      if (!list) return
      const limit = container.getBoundingClientRect().bottom
      for (const child of Array.from(list.children)) {
        const row = child as HTMLElement
        const fits = row.getBoundingClientRect().bottom <= limit + 0.5
        row.style.visibility = fits ? '' : 'hidden'
      }
    }

    apply()
    // Card/viewport resize changes how many rows fit; mutations cover the list
    // mounting and headlines arriving. We only watch childList, never the style
    // attribute we set, so `apply` can't retrigger itself.
    const resize = new ResizeObserver(apply)
    resize.observe(container)
    const mutate = new MutationObserver(apply)
    mutate.observe(container, { childList: true, subtree: true })
    return () => {
      resize.disconnect()
      mutate.disconnect()
    }
  }, [containerRef])
}
