import AsyncStorage from '@react-native-async-storage/async-storage'
import { getHiddenSnapshot, unhideSource } from './hiddenSources'

/**
 * Device-local followed sources ("Your deck") — the mobile mirror of the web
 * `newsPrefsStore`. No login required: following is anonymous and lives in
 * AsyncStorage, exposed as an external store for `useSyncExternalStore`. The
 * snapshot is served from an in-memory cache (AsyncStorage is async), hydrated
 * at first use; taps made before hydration are merged in (adds win).
 *
 * An empty followed set always falls back to the seeded default deck (see
 * NewsFeed) — the wall is never blank, even after "Deselect all".
 */

const FOCUSED_KEY = 'news.focusedSources'
const EMPTY: readonly string[] = []

let focused: readonly string[] = EMPTY
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
}

const hydrate = () => {
  if (hydrated || inFlight) return
  inFlight = true
  void AsyncStorage.getItem(FOCUSED_KEY)
    .then((rawFocused) => {
      const stored = parseList(rawFocused)
      // Fold in any follows made before hydration finished (adds win).
      const merged = [...stored]
      for (const id of focused) if (!merged.includes(id)) merged.push(id)
      const hadPreHydrationTaps = focused.length > 0
      focused = merged
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
    adding && focused.length === 0 && seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : focused
  // PREPEND, not append: "what you just followed" belongs at the front of the
  // deck, matching the web store. Appending buried it behind everything else.
  focused = adding
    ? [id, ...base.filter((x) => x !== id)]
    : focused.filter((x) => x !== id)
  // Record it so the deck jumps to this card even when it was already on the
  // wall (a reorder, not an addition) — see getFocusRequestSnapshot.
  if (adding) focusRequest = { id, seq: focusRequest.seq + 1 }
  if (adding) unhideSource(id)
  persist()
  emit()
}

let focusRequest: { id: string | null; seq: number } = { id: null, seq: 0 }

/** The most recently followed source and a monotonic sequence number. The deck
 * watches the seq so it re-jumps even when the same id is followed twice.
 * Mirrors the web newsPrefsStore. */
export const getFocusRequestSnapshot = (): {
  id: string | null
  seq: number
} => focusRequest

/** Follow every id in one write ("Select all"): materialize the seed if the
 * reader is still fresh, union in the ids, and unhide them. */
/** Ceiling for one bulk follow — a deck beyond this is unnavigable anyway. */
export const MAX_BULK_FOLLOW = 60

export const followAll = (ids: string[]): void => {
  if (ids.length === 0) return
  // The roster lists the whole catalogue when nothing is typed, so an unbounded
  // "Select all" would mount thousands of cards. Take the first slice.
  ids = ids.slice(0, MAX_BULK_FOLLOW)
  const base =
    focused.length === 0 && seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : focused
  const next = [...base]
  for (const id of ids) if (!next.includes(id)) next.push(id)
  focused = next
  persist()
  emit()
  for (const id of ids) unhideSource(id)
}

/** Unfollow every id in one write ("Deselect all"): drop them from the
 * followed set. Deliberately does NOT hide them — the wall falls back to the
 * seeded default deck (never blank), so blacklisting the whole catalogue here
 * would leave nothing to seed from. */
export const unfollowAll = (ids: string[]): void => {
  if (ids.length === 0) return
  const idSet = new Set(ids)
  focused = focused.filter((x) => !idSet.has(x))
  persist()
  emit()
}

/** Remove a source from the followed set (e.g. "Unfollow" on a card). Pruning
 * a not-yet-followed *seeded* suggestion (it's hidden separately) is a no-op
 * here — otherwise the remaining seeded deck would vanish. Mirrors web
 * `hideSource`. */
export const removeFocus = (id: string): void => {
  if (!focused.includes(id)) return
  focused = focused.filter((x) => x !== id)
  persist()
  emit()
}
