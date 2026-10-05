/**
 * Device-local reader preferences: the followed and hidden cards, the chosen
 * Starters and briefing profiles, collapsed briefings and the first-visit
 * flag. The reducers are pure; `createPrefsStore` binds them to an injected
 * storage (localStorage on the web, an in-memory mirror of AsyncStorage in
 * the app) and exposes an external store for `useSyncExternalStore`.
 *
 * The stored keys keep their original spelling on purpose: they are written
 * on readers' devices, and renaming one would read as "never followed".
 */

export const PREF_KEYS = Object.freeze({
  focused: 'news.focusedSources',
  hidden: 'news.hiddenSources',
  templates: 'news.activeTemplates',
  profiles: 'news.briefingProfiles',
  collapsed: 'news.collapsedBriefings',
  firstVisit: 'news:first-visit:v1',
  mutedWords: 'news.mutedWords',
  cardPositions: 'news-deck-active',
  edition: 'news.wallTheme',
  look: 'news.wallLook',
  readItems: 'news.readItems',
})

/** Synchronous key-value storage. The web passes `localStorage`; the app
 * passes a mirror that is hydrated from AsyncStorage and writes through. */
export interface PrefsStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

export const createMemoryStorage = (
  initial: Readonly<Record<string, string>> = {},
): PrefsStorage => {
  const map = new Map(Object.entries(initial))
  return {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => {
      map.set(key, value)
    },
    removeItem: (key) => {
      map.delete(key)
    },
  }
}

export const EMPTY_LIST: readonly string[] = Object.freeze([])

/** A stored list, tolerant of junk: anything but an array of strings is empty. */
export const parseStringList = (raw: string | null): string[] => {
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

export interface PrefsState {
  /** Followed cards, newest follow first. */
  focused: readonly string[]
  /** Unfollowed from a card; out of the deck until followed again. */
  hidden: readonly string[]
  /** Starters the reader toggled on. */
  templates: readonly string[]
  /** Briefing profiles the reader follows. */
  profiles: readonly string[]
  /** Briefing cards collapsed to their header. */
  collapsed: readonly string[]
  /** True once a card set was ever written on this device, `[]` included.
   * Tells a fresh visitor pruning the seed from a reader who emptied it. */
  touched: boolean
}

export const EMPTY_PREFS: PrefsState = Object.freeze({
  focused: EMPTY_LIST,
  hidden: EMPTY_LIST,
  templates: EMPTY_LIST,
  profiles: EMPTY_LIST,
  collapsed: EMPTY_LIST,
  touched: false,
})

/** True when the reader explicitly emptied the card set: the wall shows the
 * empty state instead of re-seeding. */
export const isCleared = (state: PrefsState): boolean =>
  state.touched && state.focused.length === 0

// Hard ceiling on the card set: every followed id mounts a card and is
// stringified on each change. Newest follows sit at the front, so the tail
// is what drops.
export const MAX_CARDS = 120
/** Ceiling for one bulk follow: a card set beyond this is unnavigable anyway. */
export const MAX_BULK_FOLLOW = 60

export interface PrefsChange {
  state: PrefsState
  /** The card the deck should jump to, when the change followed one. */
  focusRequest?: string
}

// The first follow while the wall only shows the seed promotes the whole seed
// into the followed set, so those cards become the reader's real card set
// instead of vanishing behind the one just followed. Seeded cards the reader
// already hid stay out.
const promoteSeed = (
  state: PrefsState,
  seed: readonly string[],
): readonly string[] =>
  state.focused.length === 0 && !state.touched && seed.length > 0
    ? seed.filter((x) => !state.hidden.includes(x))
    : state.focused

const without = (list: readonly string[], ids: ReadonlySet<string>) =>
  list.filter((x) => !ids.has(x))

export const toggleFocus = (
  state: PrefsState,
  id: string,
  seed: readonly string[] = EMPTY_LIST,
): PrefsChange => {
  const adding = !state.focused.includes(id)
  if (!adding) {
    return {
      state: {
        ...state,
        focused: state.focused.filter((x) => x !== id),
        touched: true,
      },
    }
  }
  const base = promoteSeed(state, seed)
  // The newly followed card goes to the FRONT so it is the top card at once.
  const focused = [id, ...base.filter((x) => x !== id)].slice(0, MAX_CARDS)
  // Re-following a card brings it back onto the wall.
  const hidden = state.hidden.includes(id)
    ? state.hidden.filter((x) => x !== id)
    : state.hidden
  return {
    state: { ...state, focused, hidden, touched: true },
    focusRequest: id,
  }
}

/** Follow every id in one write ("Select all"): promote the seed if the
 * reader is still fresh, put the ids at the front in the given order, and
 * unhide them. The deck jumps to the first. */
export const followAll = (
  state: PrefsState,
  ids: readonly string[],
  seed: readonly string[] = EMPTY_LIST,
): PrefsChange => {
  const slice = ids.slice(0, MAX_BULK_FOLLOW)
  const first = slice[0]
  if (first === undefined) return { state }
  const idSet = new Set(slice)
  const base = promoteSeed(state, seed)
  const focused = [...slice, ...without(base, idSet)].slice(0, MAX_CARDS)
  return {
    state: {
      ...state,
      focused,
      hidden: without(state.hidden, idSet),
      touched: true,
    },
    focusRequest: first,
  }
}

/** Replace the whole card set with exactly these ids (a Starter): the old
 * set is discarded rather than merged, and the ids are unhidden. */
export const replaceAll = (
  state: PrefsState,
  ids: readonly string[],
): PrefsChange => {
  const slice = ids.slice(0, MAX_BULK_FOLLOW)
  if (slice.length === 0) return { state }
  const idSet = new Set(slice)
  return {
    state: {
      ...state,
      focused: [...slice],
      hidden: without(state.hidden, idSet),
      touched: true,
    },
  }
}

/** Unfollow every id in one write ("Deselect all"). Writing the emptied
 * list marks the card set as cleared, so the wall shows the empty state
 * instead of re-seeding. */
export const unfollowAll = (
  state: PrefsState,
  ids: readonly string[],
): PrefsChange => {
  if (ids.length === 0) return { state }
  const idSet = new Set(ids)
  return {
    state: { ...state, focused: without(state.focused, idSet), touched: true },
  }
}

/** "Unfollow" on a card: hidden everywhere until followed again, and
 * unfollowed too. Hiding a seeded suggestion that was never followed leaves
 * the card set untouched, so the remaining seed stays. */
export const hideSource = (state: PrefsState, id: string): PrefsChange => {
  const wasFollowed = state.focused.includes(id)
  return {
    state: {
      ...state,
      hidden: state.hidden.includes(id) ? state.hidden : [...state.hidden, id],
      focused: wasFollowed
        ? state.focused.filter((x) => x !== id)
        : state.focused,
      touched: state.touched || wasFollowed,
    },
  }
}

export const unhideSource = (state: PrefsState, id: string): PrefsChange =>
  state.hidden.includes(id)
    ? { state: { ...state, hidden: state.hidden.filter((x) => x !== id) } }
    : { state }

export const setActiveTemplates = (
  state: PrefsState,
  ids: readonly string[],
): PrefsChange => ({ state: { ...state, templates: [...ids] } })

export const setBriefingProfiles = (
  state: PrefsState,
  ids: readonly string[],
): PrefsChange => ({ state: { ...state, profiles: [...ids] } })

export const toggleCollapsed = (
  state: PrefsState,
  id: string,
): PrefsChange => ({
  state: {
    ...state,
    collapsed: state.collapsed.includes(id)
      ? state.collapsed.filter((x) => x !== id)
      : [...state.collapsed, id],
  },
})

export interface FocusRequest {
  id: string | null
  /** Monotonic, so the deck re-jumps even when the same id is followed twice. */
  seq: number
}

export const NO_FOCUS_REQUEST: FocusRequest = Object.freeze({
  id: null,
  seq: 0,
})

export interface PrefsStore {
  /** Referentially stable while the stored values are unchanged. */
  getState(): PrefsState
  subscribe(listener: () => void): () => void
  /** Re-read storage and notify when it changed: after an async hydration,
   * or a write from another tab. */
  refresh(): void
  /** The seeded card set the wall currently shows, promoted on first follow. */
  setSeed(ids: readonly string[]): void
  getFocusRequest(): FocusRequest
  toggleFocus(id: string): void
  followAll(ids: readonly string[]): void
  replaceAll(ids: readonly string[]): void
  unfollowAll(ids: readonly string[]): void
  hideSource(id: string): void
  unhideSource(id: string): void
  setActiveTemplates(ids: readonly string[]): void
  setBriefingProfiles(ids: readonly string[]): void
  toggleCollapsed(id: string): void
}

type ListKey = Exclude<keyof PrefsState, 'touched'>
const LIST_KEYS: readonly ListKey[] = [
  'focused',
  'hidden',
  'templates',
  'profiles',
  'collapsed',
]
const STORAGE_KEY: Readonly<Record<ListKey, string>> = {
  focused: PREF_KEYS.focused,
  hidden: PREF_KEYS.hidden,
  templates: PREF_KEYS.templates,
  profiles: PREF_KEYS.profiles,
  collapsed: PREF_KEYS.collapsed,
}

const readRaw = (storage: PrefsStorage, key: string): string | null => {
  try {
    return storage.getItem(key)
  } catch {
    return null
  }
}

export const createPrefsStore = (storage: PrefsStorage): PrefsStore => {
  const listeners = new Set<() => void>()
  let seed: readonly string[] = EMPTY_LIST
  let focusRequest: FocusRequest = NO_FOCUS_REQUEST
  // Cached per raw string so `getState` stays referentially stable while the
  // stored values are unchanged, which `useSyncExternalStore` requires.
  const raws: Record<ListKey, string | null> = {
    focused: null,
    hidden: null,
    templates: null,
    profiles: null,
    collapsed: null,
  }
  let state: PrefsState = EMPTY_PREFS
  let primed = false
  // Storage threw on a write: from here the in-memory state is the truth
  // for this session, and reads stop consulting storage.
  let memoryOnly = false

  const emit = () => {
    for (const listener of listeners) listener()
  }

  const read = (): PrefsState => {
    if (memoryOnly) return state
    let changed = !primed
    const next: Record<ListKey, string | null> = { ...raws }
    for (const key of LIST_KEYS) {
      next[key] = readRaw(storage, STORAGE_KEY[key])
      if (next[key] !== raws[key]) changed = true
    }
    if (!changed) return state
    primed = true
    Object.assign(raws, next)
    state = {
      focused: parseStringList(next.focused),
      hidden: parseStringList(next.hidden),
      templates: parseStringList(next.templates),
      profiles: parseStringList(next.profiles),
      collapsed: parseStringList(next.collapsed),
      touched: next.focused !== null,
    }
    return state
  }

  const write = (change: PrefsChange) => {
    const before = read()
    const after = change.state
    try {
      for (const key of LIST_KEYS) {
        if (after[key] !== before[key]) {
          storage.setItem(STORAGE_KEY[key], JSON.stringify(after[key]))
        }
      }
      if (
        after.touched &&
        !before.touched &&
        after.focused === before.focused
      ) {
        storage.setItem(STORAGE_KEY.focused, JSON.stringify(after.focused))
      }
    } catch {
      // Storage full or blocked: the in-memory state still serves this session.
      memoryOnly = true
      state = after
    }
    if (change.focusRequest !== undefined) {
      focusRequest = { id: change.focusRequest, seq: focusRequest.seq + 1 }
    }
    read()
    emit()
  }

  return {
    getState: read,
    subscribe: (listener) => {
      listeners.add(listener)
      return () => {
        listeners.delete(listener)
      }
    },
    refresh: () => {
      const before = state
      if (read() !== before) emit()
    },
    setSeed: (ids) => {
      seed = ids
    },
    getFocusRequest: () => focusRequest,
    toggleFocus: (id) => write(toggleFocus(read(), id, seed)),
    followAll: (ids) => write(followAll(read(), ids, seed)),
    replaceAll: (ids) => write(replaceAll(read(), ids)),
    unfollowAll: (ids) => write(unfollowAll(read(), ids)),
    hideSource: (id) => write(hideSource(read(), id)),
    unhideSource: (id) => write(unhideSource(read(), id)),
    setActiveTemplates: (ids) => write(setActiveTemplates(read(), ids)),
    setBriefingProfiles: (ids) => write(setBriefingProfiles(read(), ids)),
    toggleCollapsed: (id) => write(toggleCollapsed(read(), id)),
  }
}

export interface StartersGate {
  storage: PrefsStorage
  /** The visitor arrived on a shared card, a share link or a topic: they
   * came for a specific card, never for a welcome. */
  deepLink?: boolean
  /** A consent banner is still up: a dialog over it would be unclickable. */
  consentPending?: boolean
}

/** First visit ever: offer the Starters once, and never over a deep link. */
export const shouldOfferStarters = (gate: StartersGate): boolean => {
  if (gate.deepLink || gate.consentPending) return false
  try {
    return (
      gate.storage.getItem(PREF_KEYS.firstVisit) === null &&
      gate.storage.getItem(PREF_KEYS.focused) === null
    )
  } catch {
    // Storage blocked (private mode): skip the welcome rather than loop it.
    return false
  }
}

/** Set the moment the welcome opens, so closing it never nags again. */
export const markStartersOffered = (storage: PrefsStorage): void => {
  try {
    storage.setItem(PREF_KEYS.firstVisit, '1')
  } catch {
    // Storage blocked: nothing to remember.
  }
}
