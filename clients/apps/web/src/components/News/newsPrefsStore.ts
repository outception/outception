'use client'

/**
 * Device-local news preferences (selected tab + followed sources) backed by
 * localStorage, exposed as an external store for `useSyncExternalStore`. This
 * is the SSR-safe way to read persisted client state: the server snapshot is a
 * stable default, so the first client render matches the server (no hydration
 * mismatch), and every subscriber re-renders when a value changes.
 */

export type NewsTab = 'focus' | 'trending'

const TAB_KEY = 'news.tab'
const FOCUSED_KEY = 'news.focusedSources'
const EMPTY: readonly string[] = []

const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

export const subscribe = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getTabSnapshot = (): NewsTab =>
  localStorage.getItem(TAB_KEY) === 'focus' ? 'focus' : 'trending'

export const getTabServerSnapshot = (): NewsTab => 'trending'

export const setTab = (tab: NewsTab): void => {
  try {
    localStorage.setItem(TAB_KEY, tab)
  } catch {
    // storage disabled — the tab just won't persist across reloads
  }
  emit()
}

// `getSnapshot` must return a referentially stable value while unchanged, or
// useSyncExternalStore loops. Cache the parsed array keyed by the raw string.
let cachedRaw: string | null = null
let cachedArr: readonly string[] = EMPTY

export const getFocusedSnapshot = (): readonly string[] => {
  let raw: string | null = null
  try {
    raw = localStorage.getItem(FOCUSED_KEY)
  } catch {
    return EMPTY
  }
  if (raw === cachedRaw) return cachedArr
  cachedRaw = raw
  try {
    const parsed = JSON.parse(raw || '[]')
    cachedArr = Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string')
      : EMPTY
  } catch {
    cachedArr = EMPTY
  }
  return cachedArr
}

export const getFocusedServerSnapshot = (): readonly string[] => EMPTY

export const toggleFocus = (id: string): void => {
  const current = getFocusedSnapshot()
  const next = current.includes(id)
    ? current.filter((x) => x !== id)
    : [...current, id]
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(next))
  } catch {
    // storage disabled — the deck just won't persist
  }
  emit()
}
