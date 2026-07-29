// Whether the elevated news card has an inline AI summary OPEN (see
// NewsSourceCard). Exposed as an external store, same pattern as
// utils/gamePlaying.ts, so the deck's pan gesture can stand down while the
// reader is inside the summary's ScrollView - a vertical drag there must
// scroll the summary, not throw the card.
let open = false
const listeners = new Set<() => void>()

// The top card's swipe executor: the open summary detects its OWN horizontal
// pan (same-component composition - the only arbitration iOS honors
// reliably) and hands the finished stroke here; the deck applies its usual
// direction/RTL/bounds rules and advances.
let swipeHandler: ((dx: number) => void) | null = null

export const setSummarySwipeHandler = (
  handler: ((dx: number) => void) | null,
): void => {
  swipeHandler = handler
}

export const getSummarySwipeHandler = () => swipeHandler

export const setSummaryOpen = (next: boolean): void => {
  if (next === open) return
  open = next
  for (const listener of listeners) listener()
}

export const subscribeSummaryOpen = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getSummaryOpenSnapshot = (): boolean => open
