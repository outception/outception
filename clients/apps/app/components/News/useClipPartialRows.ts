import { useCallback, useState } from 'react'
import type { LayoutChangeEvent } from 'react-native'

/**
 * React Native port of the web hook of the same name. The deck card doesn't
 * scroll, so its headline list is clipped by `overflow: hidden` - which slices
 * the last visible row mid-sentence. The web hides any row whose bottom falls
 * past the card; RN has no post-layout visibility pass, so instead we measure
 * the available height and each row's height, then render only the rows that
 * fit whole.
 *
 * Usage:
 *   const clip = useClipPartialRows()
 *   <Box flex={1} onLayout={clip.onContainerLayout}>
 *     {items.slice(0, clip.visibleCount).map((item, i) => (
 *       <Row key={i} onLayout={clip.onRowLayout(i)} … />
 *     ))}
 *   </Box>
 */
// Tallest phones fit ~14 of the shortest rows; 20 covers dense lists without
// shaping all 30 (see the fitting-pass comment below).
const PREMEASURE_ROWS = 20

export const useClipPartialRows = (
  total: number,
  rowGap = 0,
  // Index of a row hosting the expanded inline summary: it grows taller than
  // the remaining space by design, and clipping it away would collapse the
  // summary mid-read. Rows 0..pin always render; the card's overflow clips
  // the excess (mirrors the web hook's data-inline-summary exemption).
  pin: number | null = null,
) => {
  const [available, setAvailable] = useState(0)
  const [heights, setHeights] = useState<number[]>([])

  const onContainerLayout = useCallback((e: LayoutChangeEvent) => {
    const h = e.nativeEvent.layout.height
    setAvailable((prev) => (Math.abs(prev - h) > 0.5 ? h : prev))
  }, [])

  const onRowLayout = useCallback(
    (index: number) => (e: LayoutChangeEvent) => {
      const h = e.nativeEvent.layout.height
      setHeights((prev) => {
        if (Math.abs((prev[index] ?? 0) - h) <= 0.5) return prev
        const next = [...prev]
        next[index] = h
        return next
      })
    },
    [],
  )

  // A row that changes size and then unmounts before re-measuring (closing an
  // expanded inline summary is the case: the row balloons, the pin releases,
  // the fitting pass evicts it) leaves a stale giant height behind - and an
  // unmounted row can never report again, so the card stays clipped to a
  // couple of rows forever. Dropping the entry re-measures it on next mount.
  const invalidateRow = useCallback((index: number) => {
    setHeights((prev) => {
      if (prev[index] === undefined) return prev
      const next = [...prev]
      delete next[index]
      return next
    })
  }, [])

  // Forget measurements from *fromIndex* down and re-fit - the nuclear form
  // of invalidateRow. Closing a summary uses this: the single-row invalidation
  // provably recovers on paper, yet on-device the hero row kept freezing the
  // card at one headline until an app restart (which is exactly a full
  // remeasure). Rows ABOVE the collapsed one must keep their measurements:
  // their frames don't change, so RN never re-fires onLayout for them, and
  // wiping them left permanent holes the fitting pass could never fill
  // (the card then over-rendered 20 rows with the last sliced mid-sentence).
  const resetRows = useCallback((fromIndex = 0) => {
    setHeights((prev) =>
      prev.length > fromIndex ? prev.slice(0, Math.max(0, fromIndex)) : prev,
    )
  }, [])

  // Until the container is measured, render enough rows to overfill any phone
  // card - the tallest iPhone fits ~14 of the shortest rows. Rendering all 30
  // just to measure them was the single biggest per-swipe cost (each swipe
  // mounts a fresh card mid-animation, and text-shaping happens per row).
  // `overflow: hidden` keeps the measuring frame from spilling; if somehow
  // more rows fit, the loop below grows past the cap one row at a time.
  let visibleCount = Math.min(total, PREMEASURE_ROWS)
  const pinned = pin === null ? 0 : Math.min(pin + 1, total)
  if (available > 0 && heights.length) {
    let used = 0
    visibleCount = 0
    for (let i = 0; i < total; i += 1) {
      let h: number | undefined = heights[i]
      // A remembered height taller than the whole container is stale by
      // definition (a row that once hosted the expanded summary and
      // unmounted before re-measuring). Trust it for the pinned row only;
      // anywhere else, re-measure - a poisoned entry here used to clip the
      // card to two rows permanently.
      if (h !== undefined && h > available && i !== pin) h = undefined
      if (h === undefined) {
        // Unmeasured hole: render a full batch past it rather than exactly
        // one row. A still-mounted row whose measurement was invalidated
        // (collapsing an expanded summary) may never re-fire onLayout -
        // rendering one-at-a-time then waited forever on it and froze the
        // card at the hole. Overdraw is safe: the card clips overflow, and
        // real heights stream in to settle the count.
        visibleCount = Math.min(total, Math.max(i + 1, PREMEASURE_ROWS))
        break
      }
      // Include the gap the parent Box puts between rows, or a row that
      // only fits without its gap still gets sliced.
      const withGap = visibleCount > 0 ? h + rowGap : h
      if (used + withGap > available + 0.5) break
      used += withGap
      visibleCount = i + 1
    }
    // Always show at least the lead story, even on a very short card.
    visibleCount = Math.max(1, visibleCount)
  }
  visibleCount = Math.max(visibleCount, pinned)

  return {
    onContainerLayout,
    onRowLayout,
    invalidateRow,
    resetRows,
    visibleCount,
  }
}
