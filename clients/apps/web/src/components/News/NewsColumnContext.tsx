'use client'

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  useSyncExternalStore,
  type PropsWithChildren,
} from 'react'
import {
  getEverFollowedServerSnapshot,
  getEverFollowedSnapshot,
  getFocusedServerSnapshot,
  getFocusedSnapshot,
  getHiddenServerSnapshot,
  getHiddenSnapshot,
  hideSource as storeHideSource,
  subscribe,
  toggleFocus as storeToggleFocus,
} from './newsPrefsStore'

interface NewsColumnState {
  /** Whether the source-search palette ("More" / ⌘K) is open. */
  searchOpen: boolean
  setSearchOpen: (open: boolean) => void
  /** Device-local followed source ids (no login required). */
  focused: readonly string[]
  toggleFocus: (id: string) => void
  isFocused: (id: string) => boolean
  /** Sources unfollowed from a card — hidden from the wall until re-followed. */
  hidden: readonly string[]
  hideSource: (id: string) => void
  /** True once the user has ever followed (or unfollowed a followed) source. */
  everFollowed: boolean
  /** Sources whose feed failed to load — dropped from the deck so dead cards
   * never show. */
  isFailed: (id: string) => boolean
  markFailed: (id: string) => void
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
  const everFollowed = useSyncExternalStore(
    subscribe,
    getEverFollowedSnapshot,
    getEverFollowedServerSnapshot,
  )
  const [searchOpen, setSearchOpen] = useState(false)
  const [failed, setFailed] = useState<Set<string>>(() => new Set())

  const isFocused = useCallback((id: string) => focused.includes(id), [focused])

  const markFailed = useCallback((id: string) => {
    setFailed((prev) => {
      if (prev.has(id)) return prev
      const next = new Set(prev)
      next.add(id)
      return next
    })
  }, [])

  const isFailed = useCallback((id: string) => failed.has(id), [failed])

  const value = useMemo(
    () => ({
      searchOpen,
      setSearchOpen,
      focused,
      toggleFocus: storeToggleFocus,
      isFocused,
      hidden,
      hideSource: storeHideSource,
      everFollowed,
      isFailed,
      markFailed,
    }),
    [
      searchOpen,
      focused,
      isFocused,
      hidden,
      everFollowed,
      isFailed,
      markFailed,
    ],
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
