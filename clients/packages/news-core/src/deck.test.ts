import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import {
  composeDeck,
  composeDefaultDeck,
  finalizeDeck,
  resolveRef,
  type DeckData,
  type DeckInput,
} from './deck'

const KNOWN = new Set([
  'gnews-ie',
  'bbc-world',
  'youtube-guardian',
  'thehill',
  'sport-gaelic-football',
  'sport-hurling',
  'bbcsport',
  'heatmap-ucl',
  'heatmap-premier-league',
  'property-ie',
  'live-quakes',
  'weather',
])

const DATA: DeckData = {
  base: [
    { id: 'bbc-world', injectAfter: ['youtube-guardian'] },
    { id: 'thehill', injectAfter: ['country:property'] },
    { id: 'bbcsport', swap: 'sports' },
    { id: 'heatmap-ucl', swap: 'sport_tables' },
    { id: 'live-quakes', enabled: false },
    { id: 'live-storms', season: [6, 11], countries: ['US'] },
    { id: 'weather' },
  ],
  countryTables: {
    IE: {
      sports: ['sport-gaelic-football', 'sport-hurling'],
      sport_tables: ['heatmap-premier-league'],
      property: ['property-ie'],
    },
  },
}

const input = (
  country: string | null,
  extra: Partial<DeckInput> = {},
): DeckInput => ({
  country,
  month: 3,
  known: (id) => KNOWN.has(id),
  disabled: () => false,
  ...extra,
})

describe('composeDefaultDeck', () => {
  it('swaps and injects per country', () => {
    expect(composeDefaultDeck(DATA, input('IE'))).toEqual([
      'gnews-ie',
      'bbc-world',
      'youtube-guardian',
      'thehill',
      'property-ie',
      'sport-gaelic-football',
      'sport-hurling',
      'heatmap-premier-league',
      'weather',
    ])
  })

  it('keeps generic entries for an unknown country', () => {
    expect(composeDefaultDeck(DATA, input('FR'))).toEqual([
      'bbc-world',
      'youtube-guardian',
      'thehill',
      'bbcsport',
      'heatmap-ucl',
      'weather',
    ])
  })

  it('gates on enabled, season and country', () => {
    const known = (id: string) => KNOWN.has(id) || id === 'live-storms'
    expect(
      composeDefaultDeck(DATA, input('US', { month: 8, known })),
    ).toContain('live-storms')
    expect(
      composeDefaultDeck(DATA, input('US', { month: 3, known })),
    ).not.toContain('live-storms')
    expect(
      composeDefaultDeck(DATA, input('IE', { month: 8, known })),
    ).not.toContain('live-storms')
    expect(composeDefaultDeck(DATA, input('IE'))).not.toContain('live-quakes')
  })

  it('puts the shared card and the country card first', () => {
    const deck = composeDefaultDeck(
      DATA,
      input('IE', { sharedCard: 'thehill' }),
    )
    expect(deck.slice(0, 2)).toEqual(['thehill', 'gnews-ie'])
    expect(deck.filter((id) => id === 'thehill')).toHaveLength(1)
  })

  it('resolves country refs with fallbacks', () => {
    expect(resolveRef('country:news', DATA, 'IE')).toEqual(['gnews-ie'])
    expect(resolveRef('country:news', DATA, null)).toEqual([])
    expect(resolveRef('country:podcast|podcast-x', DATA, 'IE')).toEqual([
      'podcast-x',
    ])
    expect(resolveRef('country:property', DATA, 'IE')).toEqual(['property-ie'])
    expect(resolveRef('plain', DATA, null)).toEqual(['plain'])
  })
})

describe('finalizeDeck', () => {
  it('drops disabled, unknown and fallback ids and pins the weather strip', () => {
    expect(
      finalizeDeck(
        ['weather', 'nope', 'thehill', 'bbc-world', 'bbcsport', 'bbc-world'],
        {
          known: (id) => KNOWN.has(id),
          disabled: (id) => id === 'thehill',
          fallback: (id) => id === 'bbcsport',
        },
      ),
    ).toEqual(['bbc-world', 'weather'])
  })

  it('caps the content but never the strip', () => {
    const many = Array.from({ length: 130 }, (_, i) => `s${i}`)
    const out = finalizeDeck([...many, 'weather'], {
      known: () => true,
      disabled: () => false,
    })
    expect(out).toHaveLength(121)
    expect(out.at(-1)).toBe('weather')
  })
})

describe('shared fixture', () => {
  const fixture = JSON.parse(
    readFileSync(
      new URL(
        '../../../../server/tests/cards/fixtures/compose.json',
        import.meta.url,
      ),
      'utf8',
    ),
  ) as {
    data: DeckData
    cases: {
      name: string
      input: {
        country: string | null
        month: number
        known: string[]
        disabled: string[]
        fallback: string[]
        sharedCard: string | null
      }
      expected: string[]
    }[]
  }

  it('reproduces every case the server composer produced', () => {
    expect(fixture.cases.length).toBeGreaterThanOrEqual(8)
    for (const c of fixture.cases) {
      const known = new Set(c.input.known)
      const disabled = new Set(c.input.disabled)
      const fallback = new Set(c.input.fallback)
      expect(
        composeDefaultDeck(fixture.data, {
          country: c.input.country,
          month: c.input.month,
          known: (id) => known.has(id),
          disabled: (id) => disabled.has(id),
          fallback: (id) => fallback.has(id),
          sharedCard: c.input.sharedCard,
        }),
        c.name,
      ).toEqual(c.expected)
    }
  })
})

describe('composeDeck', () => {
  it('uses the seed for a fresh visitor and the followed set otherwise', () => {
    expect(composeDeck({ followed: [], seed: ['a', 'b'] })).toEqual(['a', 'b'])
    expect(composeDeck({ followed: ['c'], seed: ['a', 'b'] })).toEqual(['c'])
    expect(composeDeck({ followed: [], seed: ['a'], cleared: true })).toEqual(
      [],
    )
  })

  it('applies the precedence rule', () => {
    expect(
      composeDeck({
        followed: ['x', 'gnews-ie', 'y'],
        countryCard: 'gnews-ie',
      }),
    ).toEqual(['gnews-ie', 'x', 'y'])
    expect(
      composeDeck({
        followed: ['x', 'gnews-ie'],
        countryCard: 'gnews-ie',
        sharedCard: 'shared',
      }),
    ).toEqual(['shared', 'x', 'gnews-ie'])
  })

  it('does not pin a country card the reader does not hold', () => {
    expect(composeDeck({ followed: ['x'], countryCard: 'gnews-ie' })).toEqual([
      'x',
    ])
  })

  it('drops hidden and dropped ids but never the shared card', () => {
    expect(
      composeDeck({
        followed: ['a', 'b', 'c'],
        hidden: ['b', 's'],
        dropped: (id) => id === 'c' || id === 's',
        sharedCard: 's',
      }),
    ).toEqual(['s', 'a'])
  })

  it('dedupes and caps', () => {
    const many = Array.from({ length: 200 }, (_, i) => `s${i}`)
    expect(composeDeck({ followed: [...many, 's1'], cap: 10 })).toHaveLength(10)
  })
})
