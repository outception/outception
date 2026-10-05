import { describe, expect, it } from 'vitest'
import { FLAGS, createFlagStore, createListStore } from './lists'
import { PREF_KEYS, createMemoryStorage } from './prefs'
import { collapseStories, hasCoverage, hideRead } from './stories'

describe('createListStore', () => {
  it('appends, bounds, toggles and notifies', () => {
    const storage = createMemoryStorage()
    const store = createListStore(storage, 'k', { max: 3 })
    let n = 0
    store.subscribe(() => {
      n += 1
    })
    store.add('a')
    store.add('b')
    store.add('a')
    store.add('c')
    store.add('d')
    expect(store.get()).toEqual(['b', 'c', 'd'])
    expect(store.has('a')).toBe(false)
    store.toggle('b')
    store.toggle('e')
    expect(store.get()).toEqual(['c', 'd', 'e'])
    expect(JSON.parse(storage.getItem('k')!)).toEqual(['c', 'd', 'e'])
    expect(n).toBe(6)
    store.remove('zz')
    expect(n).toBe(6)
    store.clear()
    expect(store.get()).toEqual([])
  })

  it('flags live under their own key', () => {
    const storage = createMemoryStorage()
    const flags = createFlagStore(storage)
    flags.toggle(FLAGS.hideRead)
    expect(JSON.parse(storage.getItem(PREF_KEYS.flags)!)).toEqual(['hide-read'])
  })
})

describe('stories', () => {
  const items = [
    { id: '1', clusterId: 'x', publisherCount: 3 },
    { id: '2', clusterId: null },
    { id: '3', clusterId: 'x', publisherCount: 3 },
    { id: '4', clusterId: 'y', publisherCount: 1 },
  ]

  it('keeps one row per story and every unclustered row', () => {
    expect(collapseStories(items).map((i) => i.id)).toEqual(['1', '2', '4'])
  })

  it('marks coverage and hides read rows', () => {
    expect(hasCoverage(items[0]!)).toBe(true)
    expect(hasCoverage(items[3]!)).toBe(false)
    expect(hideRead(items, new Set(['2'])).map((i) => i.id)).toEqual([
      '1',
      '3',
      '4',
    ])
    expect(hideRead(items, (id) => id === '1').length).toBe(3)
  })
})

describe('flag defaults', () => {
  it('auto-play is on until declined, and the decline survives', async () => {
    const { FLAG_DEFAULTS, flagOn, offMark, setFlag, toggleFlagOn } =
      await import('./lists')
    const storage = createMemoryStorage()
    const store = createFlagStore(storage)
    expect(FLAG_DEFAULTS[FLAGS.autoplay]).toBe(true)
    expect(flagOn(store.get(), FLAGS.autoplay)).toBe(true)
    expect(flagOn(store.get(), FLAGS.hideRead)).toBe(false)
    toggleFlagOn(store, FLAGS.autoplay)
    expect(flagOn(store.get(), FLAGS.autoplay)).toBe(false)
    expect(store.get()).toEqual([offMark(FLAGS.autoplay)])
    setFlag(store, FLAGS.autoplay, true)
    expect(store.get()).toEqual([FLAGS.autoplay])
    // A reader who switched it on before the default changed stays on.
    setFlag(store, FLAGS.hideRead, true)
    expect(flagOn(store.get(), FLAGS.hideRead)).toBe(true)
  })
})

describe('rankByCoverage', () => {
  it('lifts the widest-reported cards and keeps the rest in place', async () => {
    const { rankByCoverage } = await import('./stories')
    const coverage: Record<string, number> = { b: 4, d: 2 }
    expect(rankByCoverage(['a', 'b', 'c', 'd'], (id) => coverage[id])).toEqual([
      'b',
      'd',
      'a',
      'c',
    ])
    expect(rankByCoverage([], () => 1)).toEqual([])
  })
})

describe('liftCoverage', () => {
  it('puts the widely carried stories first and keeps the rest in order', async () => {
    const { liftCoverage } = await import('./stories')
    const rows = [
      { id: 'a', publisherCount: 1 },
      { id: 'b', publisherCount: 3 },
      { id: 'c' },
      { id: 'd', publisherCount: 2 },
      { id: 'e', publisherCount: 1 },
    ]
    expect(liftCoverage(rows).map((r) => r.id)).toEqual([
      'b',
      'd',
      'a',
      'c',
      'e',
    ])
    expect(liftCoverage([{ id: 'x' }, { id: 'y' }]).map((r) => r.id)).toEqual([
      'x',
      'y',
    ])
  })
})
