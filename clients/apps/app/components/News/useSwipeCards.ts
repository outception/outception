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
import { storage } from '@/utils/prefs'

const readPositions = () => parsePositions(storage.getItem(CARD_POSITIONS_KEY))

const persistActive = (column: string, id: string): void => {
  storage.setItem(
    CARD_POSITIONS_KEY,
    JSON.stringify(withPosition(readPositions(), column, id)),
  )
}

/**
 * Owns the card set's position: which card is on top and the prev/next
 * moves, anchored by CARD ID (not index) so adding or reordering cards never
 * yanks the deck around. With a `storageKey` the active card is persisted
 * per key in the same map the web uses, so a relaunch resumes where the
 * reader left off. The rules live in news-core; the gesture stays in the
 * swipe card.
 */
// Survives card set remounts (see the focus effect below).
let consumedFocusSeq = 0

export const useSwipeCards = (
  items: string[],
  storageKey?: string,
  focusRequest?: { id: string | null; seq: number },
  initialActiveId?: string,
) => {
  // The storage mirror is hydrated at launch, so the first paint lands on
  // the saved card without a visible jump.
  const [index, setIndex] = useState(() =>
    initialIndex(
      items,
      storageKey ? readPositions()[storageKey] : undefined,
      initialActiveId,
    ),
  )
  const activeRef = useRef(items[index])
  const prevItems = useRef(items)

  // Wrap around so the deck loops endlessly; a single card stays put.
  const move = useCallback(
    (to: number) => {
      if (items.length === 0) return
      const next = wrapIndex(to, items.length)
      setIndex(next)
      const id = items[next]
      if (id) {
        activeRef.current = id
        if (storageKey) persistActive(storageKey, id)
      }
    },
    [items, storageKey],
  )

  // Jump to the just-followed card whenever a new follow is requested. This
  // covers the case the change-effect below misses: following a card that
  // was already on the wall is a reorder, not an addition. Module-scoped,
  // not a ref: the deck can remount, and a per-instance ref would
  // re-initialise to the already-bumped seq and swallow the jump.
  const lastFocusSeq = useRef(consumedFocusSeq)
  useEffect(() => {
    if (!focusRequest || focusRequest.id == null) return
    if (focusRequest.seq === lastFocusSeq.current) return
    const i = items.indexOf(focusRequest.id)
    // Only consume the request once the target is actually on the wall.
    if (i < 0) return
    lastFocusSeq.current = focusRequest.seq
    consumedFocusSeq = focusRequest.seq
    move(i)
  }, [focusRequest, items, move])

  const goNext = useCallback(() => move(index + 1), [move, index])
  const goPrev = useCallback(() => move(index - 1), [move, index])

  useEffect(() => {
    const { index: target } = resolveIndexOnChange(
      items,
      prevItems.current,
      activeRef.current,
      index,
    )
    prevItems.current = items
    const next = clampIndex(target, items.length)
    if (next !== index) {
      setIndex(next)
      activeRef.current = items[next]
    }
  }, [items, index])

  return {
    index,
    position: index + 1,
    total: items.length,
    canPrev: items.length > 1,
    canNext: items.length > 1,
    goNext,
    goPrev,
    goTo: move,
  }
}
