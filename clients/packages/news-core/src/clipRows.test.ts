import { describe, expect, it } from 'vitest'
import { PREMEASURE_ROWS, fitRowBottoms, fitRows } from './clipRows'

describe('fitRows', () => {
  it('renders a measuring batch until the container is known', () => {
    expect(fitRows({ total: 30, available: 0, heights: [] })).toBe(
      PREMEASURE_ROWS,
    )
    expect(fitRows({ total: 5, available: 0, heights: [] })).toBe(5)
  })

  it('fits whole rows including the gap', () => {
    expect(
      fitRows({ total: 5, available: 100, heights: [30, 30, 30, 30, 30] }),
    ).toBe(3)
    expect(
      fitRows({
        total: 5,
        available: 100,
        heights: [30, 30, 30, 30, 30],
        rowGap: 10,
      }),
    ).toBe(2)
  })

  it('always shows the lead story and the pinned row', () => {
    expect(fitRows({ total: 3, available: 50, heights: [40, 40, 40] })).toBe(1)
    expect(
      fitRows({
        total: 5,
        available: 100,
        heights: [30, 30, 30, 30, 30],
        pin: 4,
      }),
    ).toBe(5)
  })

  it('overdraws past an unmeasured hole and distrusts a stale giant', () => {
    expect(
      fitRows({ total: 30, available: 100, heights: [30, undefined, 30] }),
    ).toBe(PREMEASURE_ROWS)
    expect(
      fitRows({
        total: 30,
        available: 100,
        heights: [500, 30, 30],
        premeasure: 4,
      }),
    ).toBe(4)
    expect(
      fitRows({ total: 3, available: 100, heights: [500, 30, 30], pin: 0 }),
    ).toBe(1)
  })
})

describe('fitRowBottoms', () => {
  it('keeps rows above the limit and the expanded row always', () => {
    expect(fitRowBottoms([10, 50, null, 90.4, 120], 90)).toEqual([
      true,
      true,
      true,
      true,
      false,
    ])
  })
})
