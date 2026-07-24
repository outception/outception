import AsyncStorage from '@react-native-async-storage/async-storage'
import { useCallback, useEffect, useRef, useState } from 'react'

const posKey = (key: string) => `news.deckPos.${key}`

/** Keep an index inside `[0, length - 1]`. */
const clampIndex = (to: number, length: number) =>
  Math.max(0, Math.min(to, length - 1))

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
 * Owns the deck's position: which card is on top and the prev/next moves,
 * anchored by SOURCE ID (not index) so adding/reordering sources doesn't yank
 * the deck around. With a `storageKey` the active card is persisted per key
 * (AsyncStorage) so a relaunch resumes where you left off — mirrors the web hook.
 */
export const useSwipeDeck = (items: string[], storageKey?: string) => {
  const [index, setIndex] = useState(0)
  const activeRef = useRef(items[index])
  const prevItems = useRef(items)
  // Latest items, so the async restore resolves against the current list without
  // taking `items` as an effect dep (which changes identity every render).
  const itemsRef = useRef(items)
  itemsRef.current = items

  // Restore the saved card position once per storageKey (the deck remounts per
  // column, so this runs once on mount). Depending only on `storageKey` — not
  // `items` — means a re-render during the async read can't cancel-then-skip the
  // restore; `cancelled` fires only on unmount / a storageKey change.
  useEffect(() => {
    if (!storageKey) return
    let cancelled = false
    void AsyncStorage.getItem(posKey(storageKey))
      .then((id) => {
        if (cancelled || !id) return
        const idx = itemsRef.current.indexOf(id)
        if (idx >= 0) {
          activeRef.current = id
          setIndex(idx)
        }
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [storageKey])

  // Wrap around so the deck loops endlessly: stepping past the last card lands
  // back on the first and stepping back from the first lands on the last. A
  // single-card deck just stays put.
  const move = useCallback(
    (to: number) => {
      const len = items.length
      if (len === 0) return
      const next = ((to % len) + len) % len
      setIndex(next)
      const id = items[next]
      if (id) {
        activeRef.current = id
        if (storageKey)
          void AsyncStorage.setItem(posKey(storageKey), id).catch(() => {})
      }
    },
    [items, storageKey],
  )

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
  }
}
