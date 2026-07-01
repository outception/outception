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
  getFocusedServerSnapshot,
  getFocusedSnapshot,
  getTabServerSnapshot,
  getTabSnapshot,
  setTab as storeSetTab,
  subscribe,
  toggleFocus as storeToggleFocus,
  type NewsTab,
} from './newsPrefsStore'

export type { NewsTab }

interface NewsColumnState {
  /** 'focus' = your followed sources ("Your deck"), 'trending' = all sources. */
  tab: NewsTab
  setTab: (tab: NewsTab) => void
  /** Whether the source-search palette ("More" / ⌘K) is open. */
  searchOpen: boolean
  setSearchOpen: (open: boolean) => void
  /** Device-local followed source ids (no login required). */
  focused: readonly string[]
  toggleFocus: (id: string) => void
  isFocused: (id: string) => boolean
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
  const tab = useSyncExternalStore(
    subscribe,
    getTabSnapshot,
    getTabServerSnapshot,
  )
  const focused = useSyncExternalStore(
    subscribe,
    getFocusedSnapshot,
    getFocusedServerSnapshot,
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
      tab,
      setTab: storeSetTab,
      searchOpen,
      setSearchOpen,
      focused,
      toggleFocus: storeToggleFocus,
      isFocused,
      isFailed,
      markFailed,
    }),
    [tab, searchOpen, focused, isFocused, isFailed, markFailed],
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
