/**
 * The swipe deck's position rules, shared by the web pointer hook and the
 * app gesture hook: which card is on top, how the index survives the item
 * list changing, the wrap-around move, and the saved position per column by
 * CARD ID (not index), so a reload resumes where the reader left off and
 * adding or reordering cards never yanks the deck around.
 */

/** The stored map of column to active card id. The spelling is the one
 * readers' devices already hold; renaming it would read as "never opened". */
export const CARD_POSITIONS_KEY = 'news-deck-active'

export type CardPositions = Readonly<Record<string, string>>

/** Anything but a plain object of strings is an empty map. */
export const parsePositions = (raw: string | null): CardPositions => {
  if (!raw) return {}
  try {
    const parsed: unknown = JSON.parse(raw)
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed))
      return {}
    const out: Record<string, string> = {}
    for (const [key, value] of Object.entries(parsed)) {
      if (typeof value === 'string') out[key] = value
    }
    return out
  } catch {
    return {}
  }
}

export const withPosition = (
  positions: CardPositions,
  column: string,
  id: string,
): CardPositions => ({ ...positions, [column]: id })

/** Keep an index inside `[0, length - 1]`. */
export const clampIndex = (to: number, length: number): number =>
  Math.max(0, Math.min(to, length - 1))

/** Wrap around so the deck loops: past the last card lands on the first and
 * before the first lands on the last. */
export const wrapIndex = (to: number, length: number): number => {
  if (length <= 0) return 0
  return ((to % length) + length) % length
}

/** First card to show: a shared card wins (the recipient opened the link to
 * see THAT card), then the saved card if it still exists, else the start. */
export const initialIndex = (
  items: readonly string[],
  savedId: string | null | undefined,
  preferredId?: string | null,
): number => {
  if (preferredId) {
    const i = items.indexOf(preferredId)
    if (i >= 0) return i
  }
  return Math.max(0, items.indexOf(savedId ?? ''))
}

/** Where the deck should sit after the item list changes: jump to a newly
 * added card, otherwise stay anchored on the same card by id. */
export const resolveIndexOnChange = (
  items: readonly string[],
  prevItems: readonly string[],
  activeId: string | null | undefined,
  currentIndex: number,
): { index: number; added: boolean } => {
  const added = items.find((id) => !prevItems.includes(id))
  const target =
    added !== undefined ? items.indexOf(added) : items.indexOf(activeId ?? '')
  if (target >= 0) return { index: target, added: added !== undefined }
  return { index: currentIndex, added: false }
}

export interface SwipeState {
  index: number
  activeId: string | null
}

export const swipeState = (
  items: readonly string[],
  index: number,
): SwipeState => {
  const clamped = clampIndex(index, items.length)
  return { index: clamped, activeId: items[clamped] ?? null }
}

/** Move to `to`, wrapping. A single-card stack stays put. */
export const moveTo = (items: readonly string[], to: number): SwipeState =>
  swipeState(items, wrapIndex(to, items.length))

/** Reconcile the state with a changed item list: jump to an addition, stay
 * on the same card otherwise, and always clamp so removing the active card
 * can never leave the counter past the end. */
export const reconcile = (
  state: SwipeState,
  items: readonly string[],
  prevItems: readonly string[],
): SwipeState & { added: boolean } => {
  const { index, added } = resolveIndexOnChange(
    items,
    prevItems,
    state.activeId,
    state.index,
  )
  return { ...swipeState(items, index), added }
}

/** Whether both directions are available: the deck loops, so any stack of
 * more than one card can move either way. */
export const canMove = (length: number): boolean => length > 1
