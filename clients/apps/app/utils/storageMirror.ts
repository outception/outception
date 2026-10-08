import AsyncStorage from '@react-native-async-storage/async-storage'
import type { PrefsStorage } from '@outception-com/news-core'

/**
 * The news-core stores want synchronous storage; the device only offers
 * AsyncStorage. This mirror serves reads from memory, writes through to
 * disk, and hydrates the keys it is told about once at start: until then a
 * read is empty, and a write made before hydration lands is kept over the
 * value hydration brings back.
 */
export interface StorageMirror extends PrefsStorage {
  /** Load the keys from disk; resolves when memory matches. Safe to repeat. */
  hydrate(keys: readonly string[]): Promise<void>
  hydrated(): boolean
}

export const createStorageMirror = (): StorageMirror => {
  const memory = new Map<string, string>()
  const dirty = new Set<string>()
  let done = false
  let inFlight: Promise<void> | null = null
  return {
    getItem: (key) => memory.get(key) ?? null,
    setItem: (key, value) => {
      memory.set(key, value)
      dirty.add(key)
      void AsyncStorage.setItem(key, value).catch(() => {})
    },
    removeItem: (key) => {
      memory.delete(key)
      dirty.add(key)
      void AsyncStorage.removeItem(key).catch(() => {})
    },
    hydrate: (keys) => {
      if (inFlight) return inFlight
      inFlight = AsyncStorage.multiGet([...keys])
        .then((entries) => {
          for (const [key, value] of entries) {
            if (dirty.has(key)) continue
            if (value === null) memory.delete(key)
            else memory.set(key, value)
          }
          done = true
        })
        .catch(() => {
          // Disk unreadable right now: memory serves, and the next call
          // tries again.
          inFlight = null
        })
      return inFlight
    },
    hydrated: () => done,
  }
}
