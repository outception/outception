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

    // The card's clip box: the nearest ancestor that actually clips. It is
    // both what scrolls (the inline summary scrolls it programmatically) and
    // what defines the visible bottom. The container itself is
    // overflow-visible and rides UP with that scroll, so its own bottom stops
    // being the card's edge the moment a summary opens — measuring against it
    // hid rows that were plainly on screen.
    let scroller: HTMLElement | null = container
    while (
      scroller &&
      !/hidden|auto|scroll/.test(getComputedStyle(scroller).overflowY)
    ) {
      scroller = scroller.parentElement
    }
    const scrollTarget = scroller ?? container

    const apply = () => {
      const list = container.firstElementChild
      if (!list) return
      const limit = scrollTarget.getBoundingClientRect().bottom
      const rows = Array.from(list.children) as HTMLElement[]
      // A row hosting the expanded inline summary grows taller than the
      // remaining space by design — hiding it would blank the tapped
      // headline and its summary. Always keep it; the card's overflow
      // clips the excess. All rects are read before any visibility is
      // written so the loop forces at most one reflow.
      const bottoms = rows.map((row) =>
        row.querySelector('[data-inline-summary]') !== null
          ? null
          : row.getBoundingClientRect().bottom,
      )
      rows.forEach((row, i) => {
        const bottom = bottoms[i]
        const fits = bottom === null || bottom <= limit + 0.5
        row.style.visibility = fits ? '' : 'hidden'
      })
    }

    let frame: number | null = null
    const schedule = () => {
      if (frame !== null) return
      frame = requestAnimationFrame(() => {
        frame = null
        apply()
      })
    }

    apply()
    // Card/viewport resize changes how many rows fit; mutations cover the list
    // mounting and headlines arriving. We only watch childList, never the style
    // attribute we set, so `apply` can't retrigger itself. The inline summary
    // scrolls the card's clip box programmatically (overflow is hidden, so no
    // user scrolling), which moves previously-hidden rows into view —
    // re-measure on scroll or they stay hidden and the card reads as empty
    // below the tap. Scroll events don't bubble, so the listener has to sit
    // on the element that actually scrolls (`scrollTarget` above), not this
    // overflow-visible container.
    const resize = new ResizeObserver(schedule)
    resize.observe(container)
    const mutate = new MutationObserver(schedule)
    mutate.observe(container, { childList: true, subtree: true })
    scrollTarget.addEventListener('scroll', schedule, { passive: true })
    return () => {
      if (frame !== null) cancelAnimationFrame(frame)
      resize.disconnect()
      mutate.disconnect()
      scrollTarget.removeEventListener('scroll', schedule)
    }
  }, [containerRef])
}
