'use client'

import {
  CARD_POSITIONS_KEY,
  clampIndex,
  initialIndex,
  parsePositions,
  resolveIndexOnChange,
  withPosition,
  wrapIndex,
} from '@outception-com/news-core'
import { useCallback, useEffect, useRef, useState } from 'react'
import { browserStorage } from './newsPrefsStore'

// The last follow request the card set has acted on, kept at module scope: a
// card set that remounts (the wall re-fetches card metadata after a follow)
// would otherwise re-initialise to the already-bumped seq and swallow the jump.
let consumedFocusSeq = 0

const readPositions = () =>
  parsePositions(browserStorage.getItem(CARD_POSITIONS_KEY))

/** Synchronously read the saved card id for a column so the card set resumes
 * on its first paint. */
const savedCardId = (column: string): string | undefined =>
  readPositions()[column]

const persistActive = (column: string, id: string): void => {
  try {
    browserStorage.setItem(
      CARD_POSITIONS_KEY,
      JSON.stringify(withPosition(readPositions(), column, id)),
    )
  } catch {
    // storage full or disabled: the position just won't persist
  }
}

/**
 * Owns the card set's position: which card is on top, the prev/next moves, and
 * persistence per column by CARD ID (not index) so a reload resumes where you
 * left off and adding or reordering cards doesn't yank the card set around.
 * The rules live in news-core; this hook binds them to React and localStorage.
 */
export const useSwipeCards = (
  items: string[],
  column: string,
  // When set (arriving from a shared link), the card set opens on this id,
  // overriding the persisted position.
  initialActiveId?: string,
  // Bumped whenever the reader follows a card: the card set jumps to it so
  // "what you just clicked" always lands on top, even if it was already on
  // the wall (where the added-id heuristic below wouldn't catch it).
  focusRequest?: { id: string | null; seq: number },
) => {
  const [index, setIndex] = useState(() =>
    initialIndex(items, savedCardId(column), initialActiveId),
  )
  const activeRef = useRef(items[index])
  const prevItems = useRef(items)

  // Wrap around so the card set loops endlessly: stepping past the last card
  // lands back on the first and stepping back from the first lands on the
  // last. A single-card stack just stays put.
  const move = useCallback(
    (to: number) => {
      if (items.length === 0) return
      const next = wrapIndex(to, items.length)
      setIndex(next)
      const id = items[next]
      if (id) {
        activeRef.current = id
        persistActive(column, id)
      }
    },
    [items, column],
  )

  const goNext = useCallback(() => move(index + 1), [move, index])
  const goPrev = useCallback(() => move(index - 1), [move, index])

  // Jump to the just-followed card whenever a new follow is requested. This
  // covers the case the change-effect below misses: following a card that was
  // already on the wall (a seeded suggestion) is a reorder, not an addition.
  const lastFocusSeq = useRef(consumedFocusSeq)
  useEffect(() => {
    if (!focusRequest || focusRequest.id == null) return
    if (focusRequest.seq === lastFocusSeq.current) return
    const i = items.indexOf(focusRequest.id)
    // Only consume the request once the target is actually on the wall: a
    // just-followed card arrives with the next metadata fetch, and burning
    // the seq before then loses the jump for good.
    if (i < 0) return
    lastFocusSeq.current = focusRequest.seq
    consumedFocusSeq = focusRequest.seq
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot jump keyed on focusRequest.seq; the guards above prevent any re-run cascade
    move(i)
  }, [focusRequest, items, move])

  useEffect(() => {
    const { index: target, added } = resolveIndexOnChange(
      items,
      prevItems.current,
      activeRef.current,
      index,
    )
    prevItems.current = items
    // Always clamp to the current length so removing a card (unfollowing the
    // active one) can never leave the index past the end.
    const next = clampIndex(target, items.length)
    if (next !== index) {
      setIndex(next)
      activeRef.current = items[next]
      if (added) {
        persistActive(column, items[next])
      }
    }
  }, [items, index, column])

  return {
    index,
    position: index + 1,
    total: items.length,
    // The card set loops, so both directions stay available whenever there is
    // more than one card to move between.
    canPrev: items.length > 1,
    canNext: items.length > 1,
    goNext,
    goPrev,
  }
}
