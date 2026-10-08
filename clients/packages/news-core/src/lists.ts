/**
 * Small device-local lists with injected storage: the headlines a reader
 * opened (for "hide read"), and the reader's switches (`news.flags`). Bounded
 * and tolerant, like the preference store they sit beside.
 */

import { PREF_KEYS, parseStringList, type PrefsStorage } from './prefs'

const EMPTY: readonly string[] = Object.freeze([])

export interface ListStore {
  get(): readonly string[]
  has(value: string): boolean
  subscribe(listener: () => void): () => void
  refresh(): void
  /** Append; the newest entry sits last and the oldest drops past `max`. */
  add(value: string): void
  remove(value: string): void
  toggle(value: string): void
  clear(): void
}

export const createListStore = (
  storage: PrefsStorage,
  key: string,
  { max = 500 }: { max?: number } = {},
): ListStore => {
  const listeners = new Set<() => void>()
  let raw: string | null = null
  let list: readonly string[] = EMPTY
  let primed = false
  let memoryOnly = false

  const emit = () => {
    for (const listener of listeners) listener()
  }

  const read = (): readonly string[] => {
    if (memoryOnly) return list
    let next: string | null = null
    try {
      next = storage.getItem(key)
    } catch {
      return list
    }
    if (primed && next === raw) return list
    primed = true
    raw = next
    list = parseStringList(next)
    return list
  }

  const write = (next: readonly string[]) => {
    if (next === read()) return
    list = next
    const encoded = JSON.stringify(next)
    try {
      storage.setItem(key, encoded)
      raw = encoded
    } catch {
      memoryOnly = true
    }
    emit()
  }

  const has = (value: string) => read().includes(value)

  return {
    get: read,
    has,
    subscribe: (listener) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    refresh: () => {
      const before = list
      if (read() !== before) emit()
    },
    add: (value) => {
      const current = read()
      if (current.includes(value)) return
      const next = [...current, value]
      write(next.length > max ? next.slice(next.length - max) : next)
    },
    remove: (value) => {
      const current = read()
      if (!current.includes(value)) return
      write(current.filter((x) => x !== value))
    },
    toggle: (value) => {
      const current = read()
      write(
        current.includes(value)
          ? current.filter((x) => x !== value)
          : [...current, value],
      )
    },
    clear: () => write(EMPTY),
  }
}

/** The reader's switches. Absent means the default. */
export const FLAGS = Object.freeze({
  /** Hide headlines the reader already opened. Off by default. */
  hideRead: 'hide-read',
  /** Show every outlet's copy of a story instead of one row per story.
   * Off by default: the wall collapses same-story rows. */
  showEveryOutlet: 'show-every-outlet',
  /** Let the wall play itself. Off by default. */
  autoplay: 'autoplay',
} as const)

export type Flag = (typeof FLAGS)[keyof typeof FLAGS]

/** What a switch does when the reader has not touched it. Auto-play is on:
 * the wall plays itself until the reader pauses it, and the play control
 * stays in reach. */
export const FLAG_DEFAULTS: Readonly<Record<Flag, boolean>> = Object.freeze({
  [FLAGS.hideRead]: false,
  [FLAGS.showEveryOutlet]: false,
  [FLAGS.autoplay]: true,
})

/** A switch the reader turned off is stored as `off:<flag>`, so a default
 * that is on can be declined and the choice survives a default change. */
export const offMark = (flag: Flag): string => `off:${flag}`

/** Whether a switch is on: the reader's choice first, the default after. */
export const flagOn = (flags: readonly string[], flag: Flag): boolean => {
  if (flags.includes(offMark(flag))) return false
  if (flags.includes(flag)) return true
  return FLAG_DEFAULTS[flag]
}

export const setFlag = (store: ListStore, flag: Flag, on: boolean): void => {
  if (on) {
    store.remove(offMark(flag))
    store.add(flag)
  } else {
    store.remove(flag)
    store.add(offMark(flag))
  }
}

export const toggleFlagOn = (store: ListStore, flag: Flag): void =>
  setFlag(store, flag, !flagOn(store.get(), flag))

export const createFlagStore = (storage: PrefsStorage): ListStore =>
  createListStore(storage, PREF_KEYS.flags, { max: 32 })

export const createReadStore = (storage: PrefsStorage): ListStore =>
  createListStore(storage, PREF_KEYS.readItems, { max: 500 })
