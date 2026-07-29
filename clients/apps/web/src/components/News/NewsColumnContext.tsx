'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
  type PropsWithChildren,
} from 'react'
import {
  getFocusedServerSnapshot,
  getFocusedSnapshot,
  getHiddenServerSnapshot,
  getHiddenSnapshot,
  hideSource as storeHideSource,
  subscribe,
  toggleFocus as storeToggleFocus,
} from './newsPrefsStore'

// Three consecutive polls (~3 min) before a source is treated as dead.
const FAILURES_BEFORE_DROP = 3
// Dropping unmounts the card, which stops its polling - so without a timer a
// source that recovers stays gone until the reader reloads. Give it another go.
const RETRY_DROPPED_AFTER_MS = 10 * 60_000

interface NewsColumnState {
  /** Whether the source-search palette ("More" / ⌘K) is open. */
  searchOpen: boolean
  setSearchOpen: (open: boolean) => void
  /** Device-local followed source ids (no login required). */
  focused: readonly string[]
  toggleFocus: (id: string) => void
  isFocused: (id: string) => boolean
  /** Sources unfollowed from a card - hidden from the wall until re-followed. */
  hidden: readonly string[]
  hideSource: (id: string) => void
  /** True once the user has ever followed (or unfollowed a followed) source. */
  /** Sources whose feed failed to load - dropped from the deck so dead cards
   * never show. */
  isFailed: (id: string) => boolean
  markFailed: (id: string) => void
  markLoaded: (id: string) => void
}

const NewsColumnContext = createContext<NewsColumnState | null>(null)

/** Shares the selected wall tab, search-palette state, the device-local
 * "followed" sources, and the set of failed sources between the navbar pill,
 * the search palette and the wall body. The persisted bits (tab + followed)
 * come from an external localStorage store so they're SSR-safe. */
export const NewsColumnProvider = ({ children }: PropsWithChildren) => {
  const focused = useSyncExternalStore(
    subscribe,
    getFocusedSnapshot,
    getFocusedServerSnapshot,
  )
  const hidden = useSyncExternalStore(
    subscribe,
    getHiddenSnapshot,
    getHiddenServerSnapshot,
  )
  const [searchOpen, setSearchOpen] = useState(false)
  // Consecutive failures per source, not a one-strike set: the feed polls every
  // 60s, so a single offline blip or upstream 502 used to remove a card for the
  // rest of the session with no way back - and if it was the card being read,
  // the deck shifted underneath the reader.
  const [failed, setFailed] = useState<Map<string, number>>(() => new Map())

  const isFocused = useCallback((id: string) => focused.includes(id), [focused])

  const markFailed = useCallback((id: string) => {
    setFailed((prev) => {
      const count = (prev.get(id) ?? 0) + 1
      if (count > FAILURES_BEFORE_DROP) return prev
      return new Map(prev).set(id, count)
    })
  }, [])

  const markLoaded = useCallback((id: string) => {
    setFailed((prev) => {
      if (!prev.has(id)) return prev
      const next = new Map(prev)
      next.delete(id)
      return next
    })
  }, [])

  const isFailed = useCallback(
    (id: string) => (failed.get(id) ?? 0) >= FAILURES_BEFORE_DROP,
    [failed],
  )

  // Clear the strikes on dropped sources periodically so their cards remount
  // and get a fresh chance; if the source is still dead it just drops again.
  useEffect(() => {
    const dropped = [...failed]
      .filter(([, count]) => count >= FAILURES_BEFORE_DROP)
      .map(([id]) => id)
    if (dropped.length === 0) return
    const timer = setTimeout(() => {
      setFailed((prev) => {
        const next = new Map(prev)
        for (const id of dropped) next.delete(id)
        return next
      })
    }, RETRY_DROPPED_AFTER_MS)
    return () => clearTimeout(timer)
  }, [failed])

  const value = useMemo(
    () => ({
      searchOpen,
      setSearchOpen,
      focused,
      toggleFocus: storeToggleFocus,
      isFocused,
      hidden,
      hideSource: storeHideSource,
      isFailed,
      markFailed,
      markLoaded,
    }),
    [searchOpen, focused, isFocused, hidden, isFailed, markFailed, markLoaded],
  )
  return (
    <NewsColumnContext.Provider value={value}>
      {children}
    </NewsColumnContext.Provider>
  )
}

export const useNewsColumn = (): NewsColumnState => {
  const ctx = useContext(NewsColumnContext)
  if (!ctx) {
    throw new Error('useNewsColumn must be used within a NewsColumnProvider')
  }
  return ctx
}
