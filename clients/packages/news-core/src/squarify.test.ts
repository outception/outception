import { describe, expect, it } from 'vitest'
import { squarify } from './squarify'

describe('squarify', () => {
  it('fills the box with one rect per weight', () => {
    const rects = squarify([6, 6, 4, 3, 2, 2, 1], 600, 400)
    expect(rects).toHaveLength(7)
    const area = rects.reduce((s, r) => s + r.width * r.height, 0)
    expect(area).toBeCloseTo(600 * 400, 3)
    for (const r of rects) {
      expect(r.x).toBeGreaterThanOrEqual(0)
      expect(r.y).toBeGreaterThanOrEqual(0)
      expect(r.x + r.width).toBeLessThanOrEqual(600.001)
      expect(r.y + r.height).toBeLessThanOrEqual(400.001)
    }
  })

  it('treats junk weights as zero-area tiles and never yields NaN', () => {
    const rects = squarify(
      [Number.NaN, -1, 5, Number.POSITIVE_INFINITY],
      100,
      100,
    )
    expect(rects).toHaveLength(4)
    expect(
      rects.every((r) => Number.isFinite(r.width) && Number.isFinite(r.height)),
    ).toBe(true)
    expect(rects[2]!.width * rects[2]!.height).toBeCloseTo(10_000, 3)
    expect(squarify([1, 2], 0, 100)).toEqual([
      { x: 0, y: 0, width: 0, height: 0 },
      { x: 0, y: 0, width: 0, height: 0 },
    ])
  })
})
