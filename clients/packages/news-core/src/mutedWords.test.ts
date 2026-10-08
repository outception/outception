import { describe, expect, it } from 'vitest'
import {
  addMutedWord,
  createMutedWordsStore,
  filterMuted,
  isMuted,
  normalizeMutedWord,
  removeMutedWord,
} from './mutedWords'
import { PREF_KEYS, createMemoryStorage } from './prefs'

describe('muted words', () => {
  it('normalizes, dedupes and bounds length', () => {
    expect(normalizeMutedWord('  Tariffs ')).toBe('tariffs')
    expect(normalizeMutedWord('   ')).toBeNull()
    expect(normalizeMutedWord('x'.repeat(61))).toBeNull()
    const words = addMutedWord([], 'Tariffs')
    expect(addMutedWord(words, 'tariffs')).toBe(words)
    expect(removeMutedWord(words, 'tariffs')).toEqual([])
    expect(removeMutedWord(words, 'other')).toBe(words)
  })

  it('matches case-insensitively and filters lists', () => {
    expect(isMuted('Tariffs rise again', ['tariffs'])).toBe(true)
    expect(isMuted('Tariffs rise again', [])).toBe(false)
    const items = [{ t: 'Tariffs rise' }, { t: 'Rain tomorrow' }]
    expect(filterMuted(items, ['tariffs'], (i) => i.t)).toEqual([
      { t: 'Rain tomorrow' },
    ])
    expect(filterMuted(items, [], (i) => i.t)).toBe(items)
  })

  it('store writes through and notifies', () => {
    const storage = createMemoryStorage({ [PREF_KEYS.mutedWords]: '["a"]' })
    const store = createMutedWordsStore(storage)
    let n = 0
    store.subscribe(() => {
      n += 1
    })
    expect(store.getWords()).toEqual(['a'])
    store.add('B')
    expect(JSON.parse(storage.getItem(PREF_KEYS.mutedWords)!)).toEqual([
      'a',
      'b',
    ])
    store.add('b')
    store.remove('a')
    expect(store.getWords()).toEqual(['b'])
    expect(n).toBe(2)
  })
})
