'use client'

/** Muted words/phrases: any headline containing one (case-insensitive) is
 * dropped from every card. Device-local (localStorage) like follows - works
 * logged out, never leaves the browser. */

const KEY = 'news.mutedWords'
const EMPTY: readonly string[] = []

let cache: readonly string[] | null = null
const listeners = new Set<() => void>()

const read = (): readonly string[] => {
  if (cache) return cache
  try {
    const raw = localStorage.getItem(KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    cache = Array.isArray(parsed)
      ? parsed.filter((w): w is string => typeof w === 'string')
      : EMPTY
  } catch {
    cache = EMPTY
  }
  return cache
}

const write = (words: readonly string[]) => {
  cache = words
  try {
    localStorage.setItem(KEY, JSON.stringify(words))
  } catch {
    // Storage full/blocked: the in-memory list still applies this session.
  }
  listeners.forEach((l) => l())
}

export const getMutedWords = (): readonly string[] =>
  typeof window === 'undefined' ? EMPTY : read()

/** Stable reference for useSyncExternalStore's server snapshot - a fresh
 * `[]` per render would make React see a changed store on every pass. */
export const getMutedWordsServerSnapshot = (): readonly string[] => EMPTY

export const subscribeMutedWords = (listener: () => void): (() => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export const addMutedWord = (word: string): void => {
  const w = word.trim().toLowerCase()
  if (!w || w.length > 60) return
  const current = read()
  if (current.includes(w)) return
  write([...current, w])
}

export const removeMutedWord = (word: string): void => {
  write(read().filter((x) => x !== word))
}

/** True when the headline trips any muted word. */
export const isMuted = (title: string, words: readonly string[]): boolean => {
  if (words.length === 0) return false
  const t = title.toLowerCase()
  return words.some((w) => t.includes(w))
}
