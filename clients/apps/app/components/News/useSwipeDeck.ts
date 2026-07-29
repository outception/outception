import AsyncStorage from '@react-native-async-storage/async-storage'
import { useCallback, useEffect, useRef, useState } from 'react'

const posKey = (key: string) => `news.deckPos.${key}`

// Saved positions, warmed once at app start so the deck can seed its initial
// state SYNCHRONOUSLY. Web reads localStorage inside the useState initializer
// and therefore paints straight onto the saved card; AsyncStorage can't do
// that, so without this pre-warm the deck painted card 1 and then visibly
// jumped. Same pattern as focusedSources' hydrate().
const positionCache = new Map<string, string>()
let positionsLoaded = false
let positionsInFlight = false

/** Load every saved deck position into `positionCache`. Safe to call repeatedly. */
export const warmDeckPositions = (): void => {
  if (positionsLoaded || positionsInFlight) return
  positionsInFlight = true
  void AsyncStorage.getAllKeys()
    .then((keys) => {
      const ours = keys.filter((k) => k.startsWith('news.deckPos.'))
      if (ours.length === 0) return []
      return AsyncStorage.multiGet(ours)
    })
    .then((entries) => {
      for (const [key, value] of entries ?? []) {
        if (value) positionCache.set(key, value)
      }
      positionsLoaded = true
      positionsInFlight = false
    })
    .catch(() => {
      positionsInFlight = false
    })
}

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
 * (AsyncStorage) so a relaunch resumes where you left off - mirrors the web hook.
 */
// Survives deck remounts (see the focus effect below).
let consumedFocusSeq = 0

export const useSwipeDeck = (
  items: string[],
  storageKey?: string,
  focusRequest?: { id: string | null; seq: number },
  initialActiveId?: string,
) => {
  // Seed from the warmed cache when it's there, so the first paint is already
  // on the saved card; the async restore below still covers a cold cache.
  const [index, setIndex] = useState(() => {
    // A shared-card link wins over the saved position: the recipient opened
    // this link to see THAT card.
    const sharedIndex = initialActiveId ? items.indexOf(initialActiveId) : -1
    if (sharedIndex >= 0) return sharedIndex
    if (!storageKey) return 0
    const savedId = positionCache.get(posKey(storageKey))
    const savedIndex = savedId ? items.indexOf(savedId) : -1
    return savedIndex >= 0 ? savedIndex : 0
  })
  const activeRef = useRef(items[index])
  const prevItems = useRef(items)
  // Latest items, so the async restore resolves against the current list without
  // taking `items` as an effect dep (which changes identity every render).
  const itemsRef = useRef(items)
  itemsRef.current = items
  // Set the moment a focus jump lands. The restore below is async, so without
  // this its stale saved id resolves a few ms later and snaps the deck back off
  // the card the reader just followed.
  const focusApplied = useRef(false)

  // Restore the saved card position once per storageKey (the deck remounts per
  // column, so this runs once on mount). Depending only on `storageKey` - not
  // `items` - means a re-render during the async read can't cancel-then-skip the
  // restore; `cancelled` fires only on unmount / a storageKey change.
  useEffect(() => {
    if (!storageKey) return
    let cancelled = false
    void AsyncStorage.getItem(posKey(storageKey))
      .then((id) => {
        if (cancelled || !id || focusApplied.current) return
        if (initialActiveId && itemsRef.current.includes(initialActiveId))
          return
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
  }, [storageKey, initialActiveId])

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
        if (storageKey) {
          positionCache.set(posKey(storageKey), id)
          void AsyncStorage.setItem(posKey(storageKey), id).catch(() => {})
        }
      }
    },
    [items, storageKey],
  )

  // Jump to the just-followed source whenever a new follow is requested. This
  // covers the case the change-effect below misses: following a source that was
  // already on the wall is a reorder, not an addition. Mirrors the web hook.
  // Module-scoped, not a ref: the deck can remount (e.g. the empty deck's
  // "Browse sources" state swaps DeckBody), and a per-instance ref would
  // re-initialise to the already-bumped seq on return and swallow the jump.
  // The Sources dialog now floats OVER a still-mounted deck, but remounts
  // remain possible, so the module scope stays.
  const lastFocusSeq = useRef(consumedFocusSeq)
  useEffect(() => {
    if (!focusRequest || focusRequest.id == null) return
    if (focusRequest.seq === lastFocusSeq.current) return
    const i = items.indexOf(focusRequest.id)
    // Only consume the request once the target is actually on the wall. A
    // source still loading (or filtered out as failed) would otherwise burn the
    // seq and lose the jump for good.
    if (i < 0) return
    lastFocusSeq.current = focusRequest.seq
    consumedFocusSeq = focusRequest.seq
    focusApplied.current = true
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
  }
}
