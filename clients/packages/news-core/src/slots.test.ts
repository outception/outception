import { describe, expect, it } from 'vitest'
import {
  allocate,
  compareCandidates,
  rankWithDwell,
  stableHash,
  type SlotCandidate,
} from './slots'

describe('allocate', () => {
  it('elastic shares equally and lends unused slots', () => {
    expect(allocate([10, 1, 10], 9)).toEqual([4, 1, 4])
    expect(allocate([2, 2], 10)).toEqual([2, 2])
    expect(allocate([], 5)).toEqual([])
    expect(allocate([3, 3], 0)).toEqual([0, 0])
  })

  it('weighted sizes by the square root of the count times the weight', () => {
    const out = allocate([100, 4, 1], 12, 'weighted')
    expect(out.reduce((s, v) => s + v, 0)).toBe(12)
    expect(out[0]).toBeGreaterThan(out[1]!)
    expect(out[1]).toBeGreaterThan(out[2]!)
    expect(out[2]).toBeGreaterThanOrEqual(1)
  })

  it('weighted never exceeds demand and uses every slot it can', () => {
    expect(allocate([1, 1, 50], 10, 'weighted')).toEqual([1, 1, 8])
    expect(allocate([0, 5], 4, 'weighted')).toEqual([0, 4])
    expect(allocate([5, 5], 4, 'weighted', [3, 1])).toEqual([3, 1])
  })
})

describe('compareCandidates', () => {
  const c = (over: Partial<SlotCandidate> & { id: string }): SlotCandidate =>
    over

  it('orders pinned, incumbent, score, recency, hash', () => {
    const list = [
      c({ id: 'd', publishedAt: 5 }),
      c({ id: 'c', score: 7 }),
      c({ id: 'b', incumbent: true }),
      c({ id: 'a', pinned: true }),
      c({ id: 'e', publishedAt: 9 }),
    ]
    expect([...list].sort(compareCandidates).map((x) => x.id)).toEqual([
      'a',
      'b',
      'c',
      'e',
      'd',
    ])
  })

  it('is deterministic for equal rows', () => {
    const rows = [c({ id: 'x' }), c({ id: 'y' }), c({ id: 'z' })]
    const a = [...rows].sort(compareCandidates).map((r) => r.id)
    const b = [...rows]
      .reverse()
      .sort(compareCandidates)
      .map((r) => r.id)
    expect(a).toEqual(b)
    expect(stableHash('x')).toBe(stableHash('x'))
    expect(stableHash('x')).not.toBe(stableHash('y'))
  })
})

describe('rankWithDwell', () => {
  it('keeps an incumbent inside its dwell and releases it after', () => {
    const candidates = [
      { id: 'new', score: 9 },
      { id: 'old', score: 5 },
    ]
    const first = rankWithDwell({
      candidates,
      previous: ['old'],
      placedAt: { old: 0 },
      now: 60_000,
      dwellMs: 300_000,
    })
    expect(first.order.map((c) => c.id)).toEqual(['old', 'new'])
    expect(first.placedAt).toEqual({ old: 0, new: 60_000 })
    const later = rankWithDwell({
      candidates,
      previous: ['old', 'new'],
      placedAt: first.placedAt,
      now: 400_000,
      dwellMs: 300_000,
    })
    expect(later.order.map((c) => c.id)).toEqual(['new', 'old'])
  })
})
