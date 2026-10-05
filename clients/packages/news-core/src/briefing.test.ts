import { describe, expect, it } from 'vitest'
import {
  briefingState,
  categoryQuotas,
  coverage,
  filterBriefing,
  groupByCategory,
  isBriefingStale,
  scoreTier,
} from './briefing'
import type { BriefingItem } from './card'

const item = (
  over: Partial<BriefingItem> & { clusterId: string },
): BriefingItem => ({
  title: `t-${over.clusterId}`,
  url: 'https://example.com',
  category: 'world',
  publisherCount: 1,
  leadSourceName: 'Lead',
  item: {
    id: over.clusterId,
    title: 't',
    url: 'https://example.com',
  } as BriefingItem['item'],
  ...over,
})

describe('briefing', () => {
  it('tiers scores on the 0 to 10 scale', () => {
    expect(scoreTier(10)).toBe('top')
    expect(scoreTier(7)).toBe('high')
    expect(scoreTier(5)).toBe('mid')
    expect(scoreTier(2)).toBe('low')
    expect(scoreTier(null)).toBe('low')
  })

  it('groups by category in first-seen order and quotas by weight', () => {
    const items = [
      item({ clusterId: '1', category: 'world' }),
      item({ clusterId: '2', category: 'tech' }),
      item({ clusterId: '3', category: 'world' }),
      item({ clusterId: '4', category: 'world' }),
    ]
    const groups = groupByCategory(items)
    expect(groups.map((g) => g.category)).toEqual(['world', 'tech'])
    expect(groups[0]!.items.map((i) => i.clusterId)).toEqual(['1', '3', '4'])
    const quotas = categoryQuotas(groups, 3)
    expect(quotas.reduce((s, g) => s + g.items.length, 0)).toBe(3)
    expect(quotas[1]!.items).toHaveLength(1)
  })

  it('derives staleness and coverage', () => {
    const payload = { builtAt: 1000, staleAfterMs: 500 }
    expect(isBriefingStale(payload, 1400)).toBe(false)
    expect(isBriefingStale(payload, 1600)).toBe(true)
    expect(briefingState(payload, 'nominal', 1600)).toBe('stale')
    expect(briefingState(payload, 'degraded', 1600)).toBe('degraded')
    expect(coverage({ publisherCount: 4, leadSourceName: 'X' })).toEqual({
      lead: 'X',
      others: 3,
    })
    expect(
      filterBriefing([item({ clusterId: 'a', title: 'Tariffs' })], ['tariff']),
    ).toEqual([])
  })
})
