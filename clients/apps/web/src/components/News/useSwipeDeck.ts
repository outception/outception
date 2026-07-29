'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

const NEWS_DECK_ACTIVE_KEY = 'news-deck-active'

// The last follow request the deck has acted on, kept at module scope: a
// deck that remounts (the wall re-fetches card metadata after a follow) would
// otherwise re-initialise to the already-bumped seq and swallow the jump.
let consumedFocusSeq = 0

const readActiveMap = (): Record<string, string> => {
  if (typeof window === 'undefined') return {}
  try {
    const parsed: unknown = JSON.parse(
      localStorage.getItem(NEWS_DECK_ACTIVE_KEY) || '{}',
    )
    // Anything but a plain object (a stray array, string, null…) would be
    // spread/indexed as if it were the map.
    return parsed !== null &&
      typeof parsed === 'object' &&
      !Array.isArray(parsed)
      ? (parsed as Record<string, string>)
      : {}
  } catch {
    return {}
  }
}

/** Synchronously read the saved card id for a column from localStorage so the
 * deck resumes on its first paint. */
const savedCardId = (column: string): string | undefined =>
  readActiveMap()[column]

const persistActive = (column: string, id: string): void => {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(
      NEWS_DECK_ACTIVE_KEY,
      JSON.stringify({ ...readActiveMap(), [column]: id }),
    )
  } catch {
    // storage full / disabled - position just won't persist
  }
}

/** Keep an index inside `[0, length - 1]`. */
const clampIndex = (to: number, length: number) =>
  Math.max(0, Math.min(to, length - 1))

/** First card to show: the saved one if it still exists, else the start. */
const initialIndex = (items: string[], savedId: string | undefined) =>
  Math.max(0, items.indexOf(savedId ?? ''))

/** Where the deck should sit after the item list changes: jump to a newly
 * added source, otherwise stay anchored on the same card by id. */
const resolveIndexOnChange = (
  items: string[],
  prevItems: string[],
  activeId: string | undefined,
  currentIndex: number,
): { index: number; added: boolean } => {
  const added = items.find((id) => !prevItems.includes(id))
  const target = added ? items.indexOf(added) : items.indexOf(activeId ?? '')
  if (target >= 0 && target !== currentIndex)
    return { index: target, added: Boolean(added) }
  return { index: currentIndex, added: false }
}

/**
 * Owns the deck's position: which card is on top, the prev/next moves, and
 * persistence per column by SOURCE ID (not index) so a reload resumes where
 * you left off and adding/reordering sources doesn't yank the deck around.
 */
export const useSwipeDeck = (
  items: string[],
  column: string,
  // When set (e.g. arriving from a live promotion), the deck opens on this
  // source id, overriding the persisted position.
  initialActiveId?: string,
  // Bumped whenever the reader follows a source: the deck jumps to that source
  // so "what you just clicked" always lands on top, even if it was already on
  // the wall (where the added-id heuristic below wouldn't catch it).
  focusRequest?: { id: string | null; seq: number },
) => {
  const [index, setIndex] = useState(() => {
    if (initialActiveId) {
      const i = items.indexOf(initialActiveId)
      if (i >= 0) return i
    }
    return initialIndex(items, savedCardId(column))
  })
  const activeRef = useRef(items[index])
  const prevItems = useRef(items)

  // Wrap around so the deck loops endlessly: stepping past the last card lands
  // back on the first (7/7 → 1/7) and stepping back from the first lands on the
  // last. A single-card deck just stays put.
  const move = useCallback(
    (to: number) => {
      const len = items.length
      if (len === 0) return
      const next = ((to % len) + len) % len
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

  // Jump to the just-followed source whenever a new follow is requested. This
  // covers the case the change-effect below misses: following a source that was
  // already on the wall (a seeded suggestion) is a reorder, not an addition.
  const lastFocusSeq = useRef(consumedFocusSeq)
  useEffect(() => {
    if (!focusRequest || focusRequest.id == null) return
    if (focusRequest.seq === lastFocusSeq.current) return
    const i = items.indexOf(focusRequest.id)
    // Only consume the request once the target is actually on the wall: a
    // just-followed source's card arrives with the next metadata fetch, and
    // burning the seq before then loses the jump for good.
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
    // Always clamp to the current length so removing a card (e.g. unfollowing
    // the active source) can never leave the index past the end - otherwise the
    // counter shows "2 / 1".
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
    // The deck loops, so both directions stay available whenever there is more
    // than one card to move between.
    canPrev: items.length > 1,
    canNext: items.length > 1,
    goNext,
    goPrev,
  }
}
