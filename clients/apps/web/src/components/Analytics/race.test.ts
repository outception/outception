import { describe, expect, it } from 'vitest'
import { buildFrames, lastDate, type RaceRow, trimRows } from './race'

const row = (date: string, name: string, value: number) => ({
  date,
  name,
  value,
})

describe('race helpers', () => {
  it('finds the last day', () => {
    expect(
      lastDate([row('2026-10-01', 'a', 1), row('2026-10-03', 'b', 1)]),
    ).toBe('2026-10-03')
    expect(lastDate([])).toBe('')
  })

  it('trims to the last days, ending on the latest frame', () => {
    const rows: RaceRow[] = ['01', '02', '03', '04'].map((d) =>
      row(`2026-10-${d}`, 'a', 1),
    )
    expect(trimRows(rows, 2).map((r) => r.date)).toEqual([
      '2026-10-03',
      '2026-10-04',
    ])
  })
})

describe('buildFrames', () => {
  it('ranks each frame biggest first, ties by name', () => {
    const race = buildFrames(
      [
        row('2026-10-01', 'b', 2),
        row('2026-10-01', 'a', 2),
        row('2026-10-01', 'c', 5),
      ],
      { cumulative: false, topN: 10 },
    )
    expect(race.frames[0]).toEqual([
      { name: 'c', value: 5 },
      { name: 'a', value: 2 },
      { name: 'b', value: 2 },
    ])
  })

  it('leaves out zero bars and the frames before the first value', () => {
    const race = buildFrames(
      [
        row('2026-10-01', 'a', 0),
        row('2026-10-02', 'a', 0),
        row('2026-10-02', 'b', 0),
        row('2026-10-03', 'a', 1),
        row('2026-10-03', 'b', 0),
      ],
      { cumulative: false, topN: 10 },
    )
    expect(race.dates).toEqual(['2026-10-03'])
    expect(race.frames).toEqual([[{ name: 'a', value: 1 }]])
  })

  it('carries running totals when cumulative, even through a quiet day', () => {
    const race = buildFrames(
      [
        row('2026-10-01', 'a', 2),
        row('2026-10-02', 'b', 1),
        row('2026-10-03', 'a', 3),
      ],
      { cumulative: true, topN: 10 },
    )
    expect(race.frames.map((f) => f.map((b) => `${b.name}${b.value}`))).toEqual(
      [['a2'], ['a2', 'b1'], ['a5', 'b1']],
    )
  })

  it('keeps only the top bars and lists every name ever shown, once', () => {
    const race = buildFrames(
      [
        row('2026-10-01', 'a', 3),
        row('2026-10-01', 'b', 2),
        row('2026-10-01', 'c', 1),
        row('2026-10-02', 'c', 9),
        row('2026-10-02', 'a', 3),
      ],
      { cumulative: false, topN: 2 },
    )
    expect(race.frames.map((f) => f.map((b) => b.name))).toEqual([
      ['a', 'b'],
      ['c', 'a'],
    ])
    expect(race.names).toEqual(['a', 'b', 'c'])
  })
})
