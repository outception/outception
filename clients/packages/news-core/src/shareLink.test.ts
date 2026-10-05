import { describe, expect, it } from 'vitest'
import {
  buildShareLink,
  isShareLink,
  parseParams,
  parseShareLink,
  restoreFromLink,
  type RestoreLane,
} from './shareLink'
import { SHARE_TOKENS, SHARE_TOKEN_HISTORY } from './shareTokens'

describe('shareTokens', () => {
  it('never reuses or renames a token', () => {
    const tokens = Object.values(SHARE_TOKENS)
    expect(new Set(tokens).size).toBe(tokens.length)
    for (const record of SHARE_TOKEN_HISTORY) {
      expect(SHARE_TOKENS[record.meaning]).toBe(record.token)
    }
    expect(SHARE_TOKEN_HISTORY).toHaveLength(tokens.length)
    expect(Object.isFrozen(SHARE_TOKENS)).toBe(true)
  })
})

describe('parseShareLink', () => {
  it('reads the legacy query alone', () => {
    const state = parseShareLink({ search: '?card=bbc-world' })
    expect(state.lead).toBe('bbc-world')
    expect(state.cards).toEqual([])
    expect(state.version).toBeNull()
    expect(isShareLink(state)).toBe(true)
  })

  it('reads every v1 token and ignores unknown ones', () => {
    const state = parseShareLink({
      search: '?card=a',
      hash: '#v=1&c=a,b%2Cc&s=story-1&e=tide&l=noir&k=tech&at=1700000000&zz=1',
    })
    expect(state).toMatchObject({
      version: 1,
      lead: 'a',
      cards: ['a', 'b', 'c'],
      story: 'story-1',
      edition: 'tide',
      look: 'noir',
      topic: 'tech',
      at: 1700000000,
      rejected: [],
    })
  })

  it('rejects an invalid card list whole and keeps the rest', () => {
    const state = parseShareLink({ hash: '#v=1&c=ok,<bad>&e=tide' })
    expect(state.cards).toEqual([])
    expect(state.edition).toBe('tide')
    expect(state.rejected).toEqual(['cards'])
  })

  it('ignores a hash from a later version but keeps the lead', () => {
    const state = parseShareLink({ search: '?card=a', hash: '#v=2&c=a' })
    expect(state.lead).toBe('a')
    expect(state.cards).toEqual([])
    expect(state.rejected).toEqual(['hash'])
  })

  it('parses params leniently', () => {
    const map = parseParams('?a=1&b&a=2&%zz=3')
    expect(map.get('a')).toBe('1')
    expect(map.get('b')).toBe('')
    expect(map.has('%zz')).toBe(false)
  })
})

describe('buildShareLink', () => {
  it('round-trips and adds at only when asked', () => {
    const link = buildShareLink({
      lead: 'a',
      cards: ['a', 'b'],
      edition: 'tide',
      topic: 'tech',
    })
    expect(link).toBe('/?card=a#v=1&c=a,b&e=tide&k=tech')
    const [search, hash] = link.slice(1).split('#')
    const back = parseShareLink({ search: `?${search}`, hash: `#${hash}` })
    expect(back.cards).toEqual(['a', 'b'])
    expect(back.at).toBeNull()
    expect(buildShareLink({ lead: 'a', at: 12.9 })).toBe('/?card=a#v=1&at=12')
    expect(buildShareLink({ lead: 'a' })).toBe('/?card=a')
  })
})

describe('restoreFromLink', () => {
  const state = parseShareLink({
    search: '?card=a',
    hash: '#v=1&c=a,b&s=st&e=tide',
  })

  it('runs theme, cards, story in order', () => {
    const order: RestoreLane[] = []
    const result = restoreFromLink(state, {
      theme: () => {
        order.push('theme')
      },
      cards: () => {
        order.push('cards')
        return true
      },
      story: () => {
        order.push('story')
      },
    })
    expect(order).toEqual(['theme', 'cards', 'story'])
    expect(result).toEqual({
      theme: 'applied',
      cards: 'applied',
      story: 'applied',
    })
  })

  it('blocks the story when the cards did not apply and skips touched lanes', () => {
    const result = restoreFromLink(
      state,
      { theme: () => true, cards: () => false, story: () => true },
      new Set<RestoreLane>(['theme']),
    )
    expect(result).toEqual({
      theme: 'skipped',
      cards: 'blocked',
      story: 'blocked',
    })
  })
})
