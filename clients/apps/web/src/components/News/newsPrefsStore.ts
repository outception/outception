'use client'

/**
 * Device-local news preferences (selected tab + followed sources) backed by
 * localStorage, exposed as an external store for `useSyncExternalStore`. This
 * is the SSR-safe way to read persisted client state: the server snapshot is a
 * stable default, so the first client render matches the server (no hydration
 * mismatch), and every subscriber re-renders when a value changes.
 */

const FOCUSED_KEY = 'news.focusedSources'
const HIDDEN_KEY = 'news.hiddenSources'
// Set once the user has ever followed a source (or unfollowed one they had
// followed). Distinguishes a fresh visitor pruning the seeded deck — who
// should keep their remaining suggestions — from a curator whose emptied
// deck must stay empty rather than re-seeding.
const EVER_FOLLOWED_KEY = 'news.everFollowed'
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

// The ids currently seeded onto a fresh visitor's wall (the curated default
// deck). Registered by the wall while seeding so the first follow can
// materialize the whole seed into the followed set — otherwise starring one
// seeded source would collapse the deck to just that source.
let seedDeck: readonly string[] = EMPTY
export const setSeedDeck = (ids: readonly string[]): void => {
  seedDeck = ids
}

export const toggleFocus = (id: string): void => {
  const current = getFocusedSnapshot()
  const adding = !current.includes(id)
  // First follow while the wall only shows the seeded default deck: promote the
  // whole seed to the followed set so those sources become the user's real deck
  // (and the newly-starred one is added on top) instead of vanishing. Seeded
  // cards the user already unfollowed (hidden) stay out — don't resurrect them.
  const base =
    adding &&
    current.length === 0 &&
    !getEverFollowedSnapshot() &&
    seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : current
  const next = adding
    ? base.includes(id)
      ? [...base]
      : [...base, id]
    : current.filter((x) => x !== id)
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(next))
    // Any follow-list interaction marks the user a curator: following, but
    // also unfollowing — a legacy user whose follows predate the flag must
    // not get re-seeded when they un-star their last source in the palette.
    localStorage.setItem(EVER_FOLLOWED_KEY, '1')
    if (adding) {
      // Re-following a source brings it back onto the wall.
      const hidden = getHiddenSnapshot()
      if (hidden.includes(id)) {
        localStorage.setItem(
          HIDDEN_KEY,
          JSON.stringify(hidden.filter((x) => x !== id)),
        )
      }
    }
  } catch {
    // storage disabled — the deck just won't persist
  }
  emit()
}

export const getEverFollowedSnapshot = (): boolean => {
  try {
    return localStorage.getItem(EVER_FOLLOWED_KEY) === '1'
  } catch {
    return false
  }
}

/** Follow every id in one write ("Select all" in the palette): materialize the
 * seed if the reader is still fresh, union in the ids, and unhide any of them. */
export const followAll = (ids: string[]): void => {
  if (ids.length === 0) return
  const current = getFocusedSnapshot()
  const base =
    current.length === 0 && !getEverFollowedSnapshot() && seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : current
  const next = [...base]
  for (const id of ids) if (!next.includes(id)) next.push(id)
  const idSet = new Set(ids)
  const hidden = getHiddenSnapshot()
  const stillHidden = hidden.filter((h) => !idSet.has(h))
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(next))
    localStorage.setItem(EVER_FOLLOWED_KEY, '1')
    if (stillHidden.length !== hidden.length) {
      localStorage.setItem(HIDDEN_KEY, JSON.stringify(stillHidden))
    }
  } catch {
    // storage disabled — the deck just won't persist
  }
  emit()
}

/** Unfollow every id in one write ("Deselect all"): drop them from the followed
 * set and hide them, so seeded suggestions leave the wall too. */
export const unfollowAll = (ids: string[]): void => {
  if (ids.length === 0) return
  const idSet = new Set(ids)
  const next = getFocusedSnapshot().filter((x) => !idSet.has(x))
  const hidden = getHiddenSnapshot()
  const mergedHidden = [...hidden]
  for (const id of ids) if (!mergedHidden.includes(id)) mergedHidden.push(id)
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(next))
    localStorage.setItem(EVER_FOLLOWED_KEY, '1')
    localStorage.setItem(HIDDEN_KEY, JSON.stringify(mergedHidden))
  } catch {
    // storage disabled — the deck just won't persist
  }
  emit()
}

export const getEverFollowedServerSnapshot = (): boolean => false

// Hidden sources ("Unfollow" on a card): removed from the wall everywhere —
// both tabs and the seeded default deck — until re-followed from the palette.
let cachedHiddenRaw: string | null = null
let cachedHiddenArr: readonly string[] = EMPTY

export const getHiddenSnapshot = (): readonly string[] => {
  let raw: string | null = null
  try {
    raw = localStorage.getItem(HIDDEN_KEY)
  } catch {
    return EMPTY
  }
  if (raw === cachedHiddenRaw) return cachedHiddenArr
  cachedHiddenRaw = raw
  try {
    const parsed = JSON.parse(raw || '[]')
    cachedHiddenArr = Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string')
      : EMPTY
  } catch {
    cachedHiddenArr = EMPTY
  }
  return cachedHiddenArr
}

export const getHiddenServerSnapshot = (): readonly string[] => EMPTY

export const hideSource = (id: string): void => {
  try {
    const hidden = getHiddenSnapshot()
    if (!hidden.includes(id)) {
      localStorage.setItem(HIDDEN_KEY, JSON.stringify([...hidden, id]))
    }
    // Unfollowing implies un-starring too. Unfollowing a source the user had
    // actually followed marks them a curator (see EVER_FOLLOWED_KEY) —
    // hiding a mere seeded suggestion does not.
    const focused = getFocusedSnapshot()
    if (focused.includes(id)) {
      localStorage.setItem(EVER_FOLLOWED_KEY, '1')
      localStorage.setItem(
        FOCUSED_KEY,
        JSON.stringify(focused.filter((x) => x !== id)),
      )
    }
  } catch {
    // storage disabled — the removal just won't persist
  }
  emit()
}
