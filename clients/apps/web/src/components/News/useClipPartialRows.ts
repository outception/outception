'use client'

import { fitRowBottoms } from '@outception-com/news-core'
import { useEffect, type RefObject } from 'react'

/**
 * The card doesn't scroll, so its headline list is clipped by overflow,
 * which can slice the last visible row in half. This hides any row whose
 * bottom falls past the card's visible area so the clip always lands on
 * whole rows. Re-runs on resize and whenever the list's contents change.
 * The fitting rule is news-core's; this hook does the DOM measuring.
 */
export const useClipPartialRows = (
  containerRef: RefObject<HTMLElement | null>,
) => {
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // The card's clip box: the nearest ancestor that actually clips. It is
    // both what scrolls (the inline story scrolls it programmatically) and
    // what defines the visible bottom. The container itself is
    // overflow-visible and rides UP with that scroll, so its own bottom stops
    // being the card's edge the moment a story opens.
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
      // A row hosting the expanded inline story grows taller than the
      // remaining space by design; it always stays and the card's overflow
      // clips the excess. All rects are read before any visibility is
      // written so the loop forces at most one reflow.
      const bottoms = rows.map((row) =>
        row.querySelector('[data-inline-summary]') !== null
          ? null
          : row.getBoundingClientRect().bottom,
      )
      const fits = fitRowBottoms(bottoms, limit)
      rows.forEach((row, i) => {
        row.style.visibility = fits[i] ? '' : 'hidden'
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
    // Card and viewport resizes change how many rows fit; mutations cover the
    // list mounting and headlines arriving. Only childList is watched, never
    // the style attribute set here, so `apply` can't retrigger itself. The
    // inline story scrolls the card's clip box programmatically, which moves
    // previously hidden rows into view, so re-measure on scroll. Scroll
    // events don't bubble, so the listener sits on the element that scrolls.
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
