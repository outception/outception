import { useCallback, useState } from 'react'
import type { LayoutChangeEvent } from 'react-native'

/**
 * React Native port of the web hook of the same name. The deck card doesn't
 * scroll, so its headline list is clipped by `overflow: hidden` — which slices
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
export const useClipPartialRows = (total: number, rowGap = 0) => {
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

  // Until the container is measured, render everything: a first pass with all
  // rows is what lets us learn their heights. `overflow: hidden` keeps that
  // frame from spilling.
  let visibleCount = total
  if (available > 0 && heights.length) {
    let used = 0
    visibleCount = 0
    for (let i = 0; i < total; i += 1) {
      const h = heights[i]
      if (h === undefined) {
        // Not yet measured — keep it so it can report a height.
        visibleCount = i + 1
        continue
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

  return { onContainerLayout, onRowLayout, visibleCount }
}
