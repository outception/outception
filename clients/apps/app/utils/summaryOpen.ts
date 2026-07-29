// Whether the elevated news card has an inline AI summary OPEN (see
// NewsSourceCard). Exposed as an external store, same pattern as
// utils/gamePlaying.ts, so the deck's pan gesture can stand down while the
// reader is inside the summary's ScrollView — a vertical drag there must
// scroll the summary, not throw the card.
let open = false
const listeners = new Set<() => void>()

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
