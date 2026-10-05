import { fitRows } from '@outception-com/news-core'
import { useCallback, useState } from 'react'
import type { LayoutChangeEvent } from 'react-native'

/**
 * The card doesn't scroll, so its headline list is clipped by overflow,
 * which slices the last visible row mid-sentence. The fitting rule is
 * news-core's; this hook measures the container and each row on the
 * device and renders only the rows that fit whole.
 *
 * Usage:
 *   const clip = useClipPartialRows(items.length, gap, pin)
 *   <Box flex={1} onLayout={clip.onContainerLayout}>
 *     {items.slice(0, clip.visibleCount).map((item, i) => (
 *       <Row key={i} onLayout={clip.onRowLayout(i)} … />
 *     ))}
 *   </Box>
 */
export const useClipPartialRows = (
  total: number,
  rowGap = 0,
  // Index of a row hosting the expanded inline story: it grows taller than
  // the remaining space by design, and rows 0..pin always render.
  pin: number | null = null,
) => {
  const [available, setAvailable] = useState(0)
  const [heights, setHeights] = useState<(number | undefined)[]>([])

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

  // A row that changes size and then unmounts before re-measuring (closing
  // an expanded story is the case) leaves a stale giant height behind; drop
  // the entry so it re-measures on the next mount.
  const invalidateRow = useCallback((index: number) => {
    setHeights((prev) => {
      if (prev[index] === undefined) return prev
      const next = [...prev]
      delete next[index]
      return next
    })
  }, [])

  // Forget measurements from `fromIndex` down and re-fit. Rows above keep
  // theirs: their frames do not change, so the device never re-reports them.
  const resetRows = useCallback((fromIndex = 0) => {
    setHeights((prev) =>
      prev.length > fromIndex ? prev.slice(0, Math.max(0, fromIndex)) : prev,
    )
  }, [])

  const visibleCount = fitRows({ total, available, heights, rowGap, pin })

  return {
    onContainerLayout,
    onRowLayout,
    invalidateRow,
    resetRows,
    visibleCount,
  }
}
