/**
 * The card does not scroll, so its headline list is clipped by overflow,
 * which would slice the last visible row mid-sentence. Both clients hide
 * any row that does not fit whole; the measurements differ (the web reads
 * row bottoms, the app reads row heights), the fitting rules live here.
 */

// Tallest phones fit about 14 of the shortest rows; 20 covers dense lists
// without shaping all 30.
export const PREMEASURE_ROWS = 20

export interface FitRowsInput {
  total: number
  /** The container's height, 0 until measured. */
  available: number
  /** Measured row heights by index; a hole is an unmeasured row. */
  heights: readonly (number | undefined)[]
  rowGap?: number
  /** Index of the row hosting the expanded inline story: it grows taller
   * than the remaining space by design, and rows 0..pin always render. */
  pin?: number | null
  premeasure?: number
}

/** How many rows to render so the clip lands on whole rows. Until the
 * container is measured, enough rows to overfill any phone card. */
export const fitRows = (input: FitRowsInput): number => {
  const { total, available, heights, rowGap = 0, pin = null } = input
  const premeasure = input.premeasure ?? PREMEASURE_ROWS
  let visibleCount = Math.min(total, premeasure)
  const pinned = pin === null ? 0 : Math.min(pin + 1, total)
  if (available > 0 && heights.length > 0) {
    let used = 0
    visibleCount = 0
    for (let i = 0; i < total; i += 1) {
      let h: number | undefined = heights[i]
      // A remembered height taller than the whole container is stale by
      // definition (a row that once hosted the expanded story and unmounted
      // before re-measuring). Trust it for the pinned row only.
      if (h !== undefined && h > available && i !== pin) h = undefined
      if (h === undefined) {
        // Unmeasured hole: render a full batch past it rather than exactly
        // one row, or a row that never reports again freezes the card there.
        visibleCount = Math.min(total, Math.max(i + 1, premeasure))
        break
      }
      // Include the gap between rows, or a row that only fits without its
      // gap still gets sliced.
      const withGap = visibleCount > 0 ? h + rowGap : h
      if (used + withGap > available + 0.5) break
      used += withGap
      visibleCount = i + 1
    }
    // Always show at least the lead story, even on a very short card.
    visibleCount = Math.max(1, visibleCount)
  }
  return Math.max(visibleCount, pinned)
}

/** Per row, whether it fits above `limit`. A `null` bottom is the row
 * hosting the expanded story, which always shows. */
export const fitRowBottoms = (
  bottoms: readonly (number | null)[],
  limit: number,
): boolean[] =>
  bottoms.map((bottom) => bottom === null || bottom <= limit + 0.5)
