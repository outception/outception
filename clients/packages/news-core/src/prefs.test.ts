import { describe, expect, it } from 'vitest'
import {
  EMPTY_PREFS,
  MAX_BULK_FOLLOW,
  MAX_CARDS,
  PREF_KEYS,
  createMemoryStorage,
  createPrefsStore,
  followAll,
  hideSource,
  isCleared,
  markStartersOffered,
  replaceAll,
  shouldOfferStarters,
  toggleFocus,
  unfollowAll,
  type PrefsState,
} from './prefs'

const state = (over: Partial<PrefsState> = {}): PrefsState => ({
  ...EMPTY_PREFS,
  ...over,
})

describe('toggleFocus', () => {
  it('prepends a new follow and asks the deck to jump to it', () => {
    const r = toggleFocus(state({ focused: ['a'], touched: true }), 'b')
    expect(r.state.focused).toEqual(['b', 'a'])
    expect(r.focusRequest).toBe('b')
    expect(r.state.touched).toBe(true)
  })

  it('promotes the seed on the first follow, minus hidden cards', () => {
    const r = toggleFocus(state({ hidden: ['s2'] }), 'new', ['s1', 's2', 's3'])
    expect(r.state.focused).toEqual(['new', 's1', 's3'])
  })

  it('does not promote the seed once the card set was touched', () => {
    const r = toggleFocus(state({ touched: true }), 'new', ['s1'])
    expect(r.state.focused).toEqual(['new'])
  })

  it('unhides a re-followed card and unfollows on the second toggle', () => {
    const added = toggleFocus(state({ hidden: ['a'], touched: true }), 'a')
    expect(added.state.hidden).toEqual([])
    const removed = toggleFocus(added.state, 'a')
    expect(removed.state.focused).toEqual([])
    expect(removed.focusRequest).toBeUndefined()
    expect(isCleared(removed.state)).toBe(true)
  })

  it('caps the card set at the newest end', () => {
    const many = Array.from({ length: MAX_CARDS }, (_, i) => `s${i}`)
    const r = toggleFocus(state({ focused: many, touched: true }), 'fresh')
    expect(r.state.focused).toHaveLength(MAX_CARDS)
    expect(r.state.focused[0]).toBe('fresh')
    expect(r.state.focused).not.toContain(`s${MAX_CARDS - 1}`)
  })
})

describe('bulk follows', () => {
  it('followAll puts the ids first, in order, and unhides them', () => {
    const r = followAll(
      state({ focused: ['x', 'b'], hidden: ['a', 'z'], touched: true }),
      ['a', 'b'],
    )
    expect(r.state.focused).toEqual(['a', 'b', 'x'])
    expect(r.state.hidden).toEqual(['z'])
    expect(r.focusRequest).toBe('a')
  })

  it('followAll takes the first slice of a huge selection', () => {
    const ids = Array.from({ length: 500 }, (_, i) => `s${i}`)
    expect(followAll(state(), ids).state.focused).toHaveLength(MAX_BULK_FOLLOW)
  })

  it('replaceAll discards the old set', () => {
    const r = replaceAll(state({ focused: ['old'], hidden: ['a'] }), ['a', 'b'])
    expect(r.state.focused).toEqual(['a', 'b'])
    expect(r.state.hidden).toEqual([])
    expect(replaceAll(state({ focused: ['old'] }), []).state.focused).toEqual([
      'old',
    ])
  })

  it('unfollowAll clears and marks the card set cleared', () => {
    const r = unfollowAll(state({ focused: ['a', 'b'] }), ['a', 'b'])
    expect(isCleared(r.state)).toBe(true)
  })
})

describe('hideSource', () => {
  it('hides and unfollows a followed card', () => {
    const r = hideSource(state({ focused: ['a', 'b'], touched: true }), 'a')
    expect(r.state.hidden).toEqual(['a'])
    expect(r.state.focused).toEqual(['b'])
  })

  it('hiding a seeded suggestion leaves the card set untouched', () => {
    const r = hideSource(state(), 'seeded')
    expect(r.state.hidden).toEqual(['seeded'])
    expect(r.state.touched).toBe(false)
  })
})

describe('createPrefsStore', () => {
  it('reads tolerant lists and stays referentially stable', () => {
    const storage = createMemoryStorage({
      [PREF_KEYS.focused]: '["a", 1, null]',
      [PREF_KEYS.hidden]: 'junk',
    })
    const store = createPrefsStore(storage)
    const first = store.getState()
    expect(first.focused).toEqual(['a'])
    expect(first.hidden).toEqual([])
    expect(first.touched).toBe(true)
    expect(store.getState()).toBe(first)
  })

  it('writes through, notifies and bumps the focus request', () => {
    const storage = createMemoryStorage()
    const store = createPrefsStore(storage)
    let notified = 0
    store.subscribe(() => {
      notified += 1
    })
    store.setSeed(['s1', 's2'])
    store.toggleFocus('n')
    expect(JSON.parse(storage.getItem(PREF_KEYS.focused)!)).toEqual([
      'n',
      's1',
      's2',
    ])
    expect(store.getFocusRequest()).toEqual({ id: 'n', seq: 1 })
    store.toggleFocus('s1')
    store.toggleFocus('s1')
    expect(store.getFocusRequest().seq).toBe(2)
    expect(notified).toBe(3)
  })

  it('refresh picks up a write from elsewhere', () => {
    const storage = createMemoryStorage()
    const store = createPrefsStore(storage)
    expect(store.getState().focused).toEqual([])
    storage.setItem(PREF_KEYS.focused, '["x"]')
    let notified = 0
    store.subscribe(() => {
      notified += 1
    })
    store.refresh()
    expect(store.getState().focused).toEqual(['x'])
    expect(notified).toBe(1)
  })

  it('keeps serving memory when storage throws', () => {
    const storage = createMemoryStorage()
    const broken = {
      ...storage,
      setItem: () => {
        throw new Error('full')
      },
    }
    const store = createPrefsStore(broken)
    store.toggleFocus('a')
    expect(store.getState().focused).toEqual(['a'])
  })
})

describe('shouldOfferStarters', () => {
  it('offers once on a fresh device and never over a deep link', () => {
    const storage = createMemoryStorage()
    expect(shouldOfferStarters({ storage })).toBe(true)
    expect(shouldOfferStarters({ storage, deepLink: true })).toBe(false)
    expect(shouldOfferStarters({ storage, consentPending: true })).toBe(false)
    markStartersOffered(storage)
    expect(shouldOfferStarters({ storage })).toBe(false)
  })

  it('never offers to a reader who already follows', () => {
    const storage = createMemoryStorage({ [PREF_KEYS.focused]: '[]' })
    expect(shouldOfferStarters({ storage })).toBe(false)
  })

  it('skips rather than loops when storage is blocked', () => {
    const storage = {
      getItem: () => {
        throw new Error('blocked')
      },
      setItem: () => {},
      removeItem: () => {},
    }
    expect(shouldOfferStarters({ storage })).toBe(false)
    expect(() =>
      markStartersOffered({
        ...storage,
        setItem: () => {
          throw new Error('x')
        },
      }),
    ).not.toThrow()
  })
})
