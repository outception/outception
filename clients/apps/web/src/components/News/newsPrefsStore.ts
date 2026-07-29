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

// Whether this device has ever written a deck ('[]' counts). Distinguishes a
// fresh visitor — whose empty set falls back to the seeded default deck — from
// a reader who explicitly emptied their deck ("Deselect all"), which must stay
// empty rather than re-seeding.
const hasStoredDeck = (): boolean => {
  try {
    return localStorage.getItem(FOCUSED_KEY) !== null
  } catch {
    return false
  }
}

export const getDeckClearedSnapshot = (): boolean =>
  hasStoredDeck() && getFocusedSnapshot().length === 0
export const getDeckClearedServerSnapshot = (): boolean => false

// Active starter templates: which persona bundles the reader has toggled on
// (see TemplateGallery). Tracked so templates behave as combinable toggles —
// state here, the follow-set math in the gallery.
const TEMPLATES_KEY = 'news.activeTemplates'
let cachedTemplatesRaw: string | null = null
let cachedTemplatesArr: readonly string[] = EMPTY

export const getActiveTemplatesSnapshot = (): readonly string[] => {
  let raw: string | null = null
  try {
    raw = localStorage.getItem(TEMPLATES_KEY)
  } catch {
    return EMPTY
  }
  if (raw === cachedTemplatesRaw) return cachedTemplatesArr
  cachedTemplatesRaw = raw
  try {
    const parsed = JSON.parse(raw || '[]')
    cachedTemplatesArr = Array.isArray(parsed)
      ? parsed.filter((x): x is string => typeof x === 'string')
      : EMPTY
  } catch {
    cachedTemplatesArr = EMPTY
  }
  return cachedTemplatesArr
}

export const getActiveTemplatesServerSnapshot = (): readonly string[] => EMPTY

export const setActiveTemplates = (ids: readonly string[]): void => {
  try {
    localStorage.setItem(TEMPLATES_KEY, JSON.stringify(ids))
  } catch {
    // storage disabled — the toggle state just won't persist
  }
  emit()
}

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
    adding && current.length === 0 && !hasStoredDeck() && seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : current
  // Newly-followed source goes to the FRONT of the deck so it becomes the top
  // card immediately (the deck jumps to the first newly-added id). Prepending —
  // not appending — is what puts "what you just clicked" on top no matter which
  // card was showing.
  const next = adding
    ? [id, ...base.filter((x) => x !== id)].slice(0, MAX_DECK)
    : current.filter((x) => x !== id)
  // Record the just-followed source so the deck jumps to it (see
  // getFocusRequestSnapshot) regardless of whether it was already on the wall.
  if (adding) focusRequest = { id, seq: focusRequest.seq + 1 }
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(next))
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

// The source the reader most recently chose to follow, with a monotonic seq so
// the deck can jump to it EVERY time — even when it was already on the wall (a
// seeded suggestion), where a "newly added id" heuristic alone would miss it.
let focusRequest: { id: string | null; seq: number } = { id: null, seq: 0 }
const FOCUS_REQUEST_SERVER = { id: null, seq: 0 } as const
export const getFocusRequestSnapshot = (): { id: string | null; seq: number } =>
  focusRequest
export const getFocusRequestServerSnapshot = (): {
  id: string | null
  seq: number
} => FOCUS_REQUEST_SERVER

/** Follow every id in one write ("Select all" in the palette): materialize the
 * seed if the reader is still fresh, union in the ids, and unhide any of them. */
/** Ceiling for one bulk follow — a deck beyond this is unnavigable anyway. */
export const MAX_BULK_FOLLOW = 60
// Hard ceiling on the deck: every followed id mounts a card window entry and
// is stringified on each change, so repeated bulk follows can't grow it
// without bound. Newest follows sit at the front, so the tail is what drops.
export const MAX_DECK = 120

export const followAll = (ids: string[]): void => {
  if (ids.length === 0) return
  // With no query and no topic the palette lists the whole catalogue, so an
  // unbounded "Select all" would mount thousands of cards and stringify them
  // all into localStorage. Take the first slice; the deck stays usable.
  ids = ids.slice(0, MAX_BULK_FOLLOW)
  const current = getFocusedSnapshot()
  const base =
    current.length === 0 && !hasStoredDeck() && seedDeck.length > 0
      ? seedDeck.filter((x) => !getHiddenSnapshot().includes(x))
      : current
  // Bulk follows land at the FRONT too, in the given order, and the deck
  // jumps to the first of them — a tapped template behaves like a tapped
  // source: what you just chose is what you see.
  const idSet = new Set(ids)
  const next = [...ids, ...base.filter((x) => !idSet.has(x))].slice(0, MAX_DECK)
  focusRequest = { id: ids[0], seq: focusRequest.seq + 1 }
  const hidden = getHiddenSnapshot()
  const stillHidden = hidden.filter((h) => !idSet.has(h))
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(next))
    if (stillHidden.length !== hidden.length) {
      localStorage.setItem(HIDDEN_KEY, JSON.stringify(stillHidden))
    }
  } catch {
    // storage disabled — the deck just won't persist
  }
  emit()
}

/** Replace the whole deck with exactly these ids (a starter template): the
 * previous follow set is discarded rather than merged, and the template's
 * sources are unhidden so every card renders. */
export const replaceAll = (ids: string[]): void => {
  ids = ids.slice(0, MAX_BULK_FOLLOW)
  if (ids.length === 0) return
  const idSet = new Set(ids)
  const hidden = getHiddenSnapshot()
  const stillHidden = hidden.filter((h) => !idSet.has(h))
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(ids))
    if (stillHidden.length !== hidden.length) {
      localStorage.setItem(HIDDEN_KEY, JSON.stringify(stillHidden))
    }
  } catch {
    // storage disabled — the deck just won't persist
  }
  emit()
}

/** Unfollow every id in one write ("Deselect all"): drop them from the
 * followed set. Writing the emptied list marks the deck as explicitly cleared
 * (see getDeckClearedSnapshot) so the wall shows the empty state instead of
 * re-seeding the default deck. */
export const unfollowAll = (ids: string[]): void => {
  if (ids.length === 0) return
  const idSet = new Set(ids)
  const next = getFocusedSnapshot().filter((x) => !idSet.has(x))
  try {
    localStorage.setItem(FOCUSED_KEY, JSON.stringify(next))
  } catch {
    // storage disabled — the deck just won't persist
  }
  emit()
}

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
    // Unfollowing implies un-starring too.
    const focused = getFocusedSnapshot()
    if (focused.includes(id)) {
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
