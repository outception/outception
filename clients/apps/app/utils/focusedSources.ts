import AsyncStorage from '@react-native-async-storage/async-storage'
import { getHiddenSnapshot, hideSource, unhideSource } from './hiddenSources'

/**
 * Device-local followed sources ("Your deck") — the mobile mirror of the web
 * `newsPrefsStore`. No login required: following is anonymous and lives in
 * AsyncStorage, exposed as an external store for `useSyncExternalStore`. The
 * snapshot is served from an in-memory cache (AsyncStorage is async), hydrated
 * at first use; taps made before hydration are merged in (adds win).
 *
 * `everFollowed` distinguishes a fresh visitor pruning the seeded default deck
 * (who keeps their remaining suggestions) from a curator whose emptied deck
 * must stay empty rather than re-seeding.
 */

const FOCUSED_KEY = 'news.focusedSources'
const EVER_KEY = 'news.everFollowed'
const EMPTY: readonly string[] = []

let focused: readonly string[] = EMPTY
let everFollowed = false
let hydrated = false
let inFlight = false
// The ids currently seeded onto a fresh visitor's wall (the curated default
// deck); the first follow promotes the whole seed into the followed set.
let seedDeck: readonly string[] = EMPTY

const listeners = new Set<() => void>()
const emit = () => {
  for (const listener of listeners) listener()
}

const parseList = (raw: string | null): string[] => {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string')
      : []
  } catch {
    return []
  }
}

const persist = () => {
  void AsyncStorage.setItem(FOCUSED_KEY, JSON.stringify(focused)).catch(
    () => {},
  )
  void AsyncStorage.setItem(EVER_KEY, everFollowed ? '1' : '0').catch(() => {})
}

const hydrate = () => {
  if (hydrated || inFlight) return
  inFlight = true
  void Promise.all([
    AsyncStorage.getItem(FOCUSED_KEY),
    AsyncStorage.getItem(EVER_KEY),
  ])
    .then(([rawFocused, rawEver]) => {
      const stored = parseList(rawFocused)
      // Fold in any follows made before hydration finished (adds win).
      const merged = [...stored]
      for (const id of focused) if (!merged.includes(id)) merged.push(id)
      const hadPreHydrationTaps = focused.length > 0 || everFollowed
      focused = merged
      everFollowed = rawEver === '1' || hadPreHydrationTaps
      hydrated = true
      inFlight = false
      if (hadPreHydrationTaps) persist()
      emit()
    })
    .catch(() => {
      inFlight = false
    })
}

export const subscribeFocused = (listener: () => void): (() => void) => {
  hydrate()
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getFocusedSnapshot = (): readonly string[] => focused
export const getEverFollowedSnapshot = (): boolean => everFollowed

/** Register the seeded deck so the first follow can promote it into the
 * followed set (see toggleFocus) instead of collapsing the deck to one card. */
export const setSeedDeck = (ids: readonly string[]): void => {
  seedDeck = ids
}

/** Follow/unfollow a source (device-local, no login). The first follow while
 * the wall only shows the seeded default deck promotes the whole seed into the
 * followed set so those sources become the user's real deck. Adding a source
 * also restores it if it was hidden from a card. */
export const toggleFocus = (id: string): void => {
  const adding = !focused.includes(id)
  // Seeded cards the user already unfollowed (hidden) stay out of the promoted
  // set — don't resurrect them.
  const base =
    adding && focused.length === 0 && !everFollowed && seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : focused
  focused = adding
    ? base.includes(id)
      ? [...base]
      : [...base, id]
    : focused.filter((x) => x !== id)
  everFollowed = true
  if (adding) unhideSource(id)
  persist()
  emit()
}

/** Follow every id in one write ("Select all"): materialize the seed if the
 * reader is still fresh, union in the ids, and unhide them. */
export const followAll = (ids: string[]): void => {
  if (ids.length === 0) return
  const base =
    focused.length === 0 && !everFollowed && seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : focused
  const next = [...base]
  for (const id of ids) if (!next.includes(id)) next.push(id)
  focused = next
  everFollowed = true
  persist()
  emit()
  for (const id of ids) unhideSource(id)
}

/** Unfollow every id in one write ("Deselect all"): drop them from the followed
 * set and hide them, so seeded suggestions leave the wall too. */
export const unfollowAll = (ids: string[]): void => {
  if (ids.length === 0) return
  const idSet = new Set(ids)
  focused = focused.filter((x) => !idSet.has(x))
  everFollowed = true
  persist()
  emit()
  for (const id of ids) hideSource(id)
}

/** Remove a source from the followed set (e.g. "Unfollow" on a card). Only
 * removing a source the reader ACTUALLY followed marks them a curator (so an
 * emptied deck stays empty). Pruning a not-yet-followed *seeded* suggestion
 * (it's hidden separately) is a no-op here — otherwise the remaining seeded deck
 * would vanish. Mirrors web `hideSource`. */
export const removeFocus = (id: string): void => {
  if (!focused.includes(id)) return
  focused = focused.filter((x) => x !== id)
  everFollowed = true
  persist()
  emit()
}
