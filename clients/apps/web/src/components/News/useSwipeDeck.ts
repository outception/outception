'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

const NEWS_DECK_ACTIVE_KEY = 'news-deck-active'

const readActiveMap = (): Record<string, string> => {
  if (typeof window === 'undefined') return {}
  try {
    return JSON.parse(localStorage.getItem(NEWS_DECK_ACTIVE_KEY) || '{}')
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
    // storage full / disabled — position just won't persist
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

  useEffect(() => {
    const { index: target, added } = resolveIndexOnChange(
      items,
      prevItems.current,
      activeRef.current,
      index,
    )
    prevItems.current = items
    // Always clamp to the current length so removing a card (e.g. unfollowing
    // the active source) can never leave the index past the end — otherwise the
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
