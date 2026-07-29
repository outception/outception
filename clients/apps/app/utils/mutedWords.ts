import AsyncStorage from '@react-native-async-storage/async-storage'

/** Muted words/phrases: any headline containing one (case-insensitive) is
 * dropped from every card. Device-local via AsyncStorage, exposed as an
 * external store for `useSyncExternalStore` — mirrors the web store and the
 * focusedSources persistence pattern. */

const KEY = 'news.mutedWords'
const EMPTY: readonly string[] = []

let words: readonly string[] = EMPTY
let hydrated = false
const listeners = new Set<() => void>()

const emit = () => listeners.forEach((l) => l())

const persist = () => {
  void AsyncStorage.setItem(KEY, JSON.stringify(words)).catch(() => {})
}

const hydrate = () => {
  if (hydrated) return
  hydrated = true
  void AsyncStorage.getItem(KEY)
    .then((raw) => {
      if (!raw) return
      const parsed: unknown = JSON.parse(raw)
      if (Array.isArray(parsed)) {
        words = parsed.filter((w): w is string => typeof w === 'string')
        emit()
      }
    })
    .catch(() => {})
}

export const getMutedWords = (): readonly string[] => {
  hydrate()
  return words
}

export const subscribeMutedWords = (listener: () => void): (() => void) => {
  hydrate()
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export const addMutedWord = (word: string): void => {
  const w = word.trim().toLowerCase()
  if (!w || w.length > 60 || words.includes(w)) return
  words = [...words, w]
  persist()
  emit()
}

export const removeMutedWord = (word: string): void => {
  words = words.filter((x) => x !== word)
  persist()
  emit()
}

/** True when the headline trips any muted word. */
export const isMuted = (title: string, muted: readonly string[]): boolean => {
  if (muted.length === 0) return false
  const t = title.toLowerCase()
  return muted.some((w) => t.includes(w))
}
