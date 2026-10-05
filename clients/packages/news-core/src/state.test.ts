import { describe, expect, it } from 'vitest'
import {
  briefingCardId,
  briefingProfile,
  countryCardId,
  isCountryCardId,
  kindForId,
  kindForType,
  sourceFamily,
} from './card'
import {
  hasRenderableData,
  isSignalState,
  stateFromFetch,
  stateWord,
  worstState,
} from './state'

describe('state', () => {
  it('worst wins and loading sits below degraded', () => {
    expect(worstState([])).toBe('nominal')
    expect(worstState(['nominal', 'loading'])).toBe('loading')
    expect(worstState(['degraded', 'loading', 'stale'])).toBe('stale')
    expect(worstState(['unavailable', 'fallback'])).toBe('unavailable')
    expect(isSignalState('stale')).toBe(true)
    expect(isSignalState('broken')).toBe(false)
    expect(hasRenderableData('stale')).toBe(true)
    expect(hasRenderableData('unavailable')).toBe(false)
    expect(stateWord('nominal')).toBeNull()
    expect(stateWord('fallback')).toBe('fallback')
  })

  it('derives a state from a fetch', () => {
    expect(
      stateFromFetch({ loading: true, error: false, hasData: false }),
    ).toBe('loading')
    expect(stateFromFetch({ loading: true, error: false, hasData: true })).toBe(
      'nominal',
    )
    expect(stateFromFetch({ loading: false, error: true, hasData: true })).toBe(
      'stale',
    )
    expect(
      stateFromFetch({ loading: false, error: true, hasData: false }),
    ).toBe('unavailable')
  })
})

describe('card ids', () => {
  it('maps ids and types to kinds', () => {
    expect(kindForType('heatmap')).toBe('table')
    expect(kindForType(null)).toBe('feed')
    expect(() => kindForType('game')).toThrow()
    expect(kindForId('briefing:x')).toBe('briefing')
    expect(kindForId('weather')).toBe('strip')
    expect(kindForId('bbc-world', 'hottest')).toBe('feed')
    expect(briefingCardId('news-junkie')).toBe('briefing:news-junkie')
    expect(briefingProfile('briefing:news-junkie')).toBe('news-junkie')
    expect(briefingProfile('briefing:')).toBeNull()
    expect(briefingProfile('x')).toBeNull()
    expect(countryCardId('IE')).toBe('gnews-ie')
    expect(isCountryCardId('gnews-ie')).toBe(true)
    expect(isCountryCardId('gnews-world')).toBe(false)
    expect(sourceFamily('bbc-world')).toBe('bbc')
  })
})
