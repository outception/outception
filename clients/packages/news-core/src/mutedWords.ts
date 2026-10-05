/**
 * Muted words and phrases: any headline containing one (case-insensitive)
 * is dropped from every card. Device-local like follows, so it works logged
 * out and never leaves the device. The list is the same on both clients;
 * only the storage differs.
 */

import { PREF_KEYS, parseStringList, type PrefsStorage } from './prefs'

export const MUTED_WORDS_KEY = PREF_KEYS.mutedWords
export const MAX_MUTED_WORD_LENGTH = 60
const EMPTY: readonly string[] = Object.freeze([])

/** The stored form of a word: trimmed, lowercased; null when unusable. */
export const normalizeMutedWord = (word: string): string | null => {
  const w = word.trim().toLowerCase()
  return w && w.length <= MAX_MUTED_WORD_LENGTH ? w : null
}

export const parseMutedWords = (raw: string | null): string[] =>
  parseStringList(raw)

/** The list with `word` added; the same reference when nothing changed. */
export const addMutedWord = (
  words: readonly string[],
  word: string,
): readonly string[] => {
  const w = normalizeMutedWord(word)
  if (!w || words.includes(w)) return words
  return [...words, w]
}

export const removeMutedWord = (
  words: readonly string[],
  word: string,
): readonly string[] =>
  words.includes(word) ? words.filter((x) => x !== word) : words

/** True when the headline trips any muted word. */
export const isMuted = (title: string, words: readonly string[]): boolean => {
  if (words.length === 0) return false
  const t = title.toLowerCase()
  return words.some((w) => t.includes(w))
}

export const filterMuted = <T>(
  items: readonly T[],
  words: readonly string[],
  title: (item: T) => string,
): readonly T[] =>
  words.length === 0
    ? items
    : items.filter((item) => !isMuted(title(item), words))

export interface MutedWordsStore {
  getWords(): readonly string[]
  subscribe(listener: () => void): () => void
  refresh(): void
  add(word: string): void
  remove(word: string): void
}

export const createMutedWordsStore = (
  storage: PrefsStorage,
): MutedWordsStore => {
  const listeners = new Set<() => void>()
  let raw: string | null = null
  let words: readonly string[] = EMPTY
  let primed = false

  const read = (): readonly string[] => {
    let next: string | null = null
    try {
      next = storage.getItem(MUTED_WORDS_KEY)
    } catch {
      return words
    }
    if (primed && next === raw) return words
    primed = true
    raw = next
    words = parseMutedWords(next)
    return words
  }

  const write = (next: readonly string[]) => {
    if (next === read()) return
    words = next
    try {
      storage.setItem(MUTED_WORDS_KEY, JSON.stringify(next))
      raw = JSON.stringify(next)
    } catch {
      // Storage full or blocked: the in-memory list still applies this session.
      raw = JSON.stringify(next)
    }
    for (const listener of listeners) listener()
  }

  return {
    getWords: read,
    subscribe: (listener) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    refresh: () => {
      const before = words
      if (read() !== before) for (const listener of listeners) listener()
    },
    add: (word) => write(addMutedWord(read(), word)),
    remove: (word) => write(removeMutedWord(read(), word)),
  }
}
