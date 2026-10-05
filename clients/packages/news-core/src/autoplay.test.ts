import { describe, expect, it } from 'vitest'
import {
  buildTimeline,
  createManualClock,
  createRunner,
  dwellFor,
  seekTimeline,
  type AutoplayPhase,
} from './autoplay'

const cards = [
  { id: 'a', items: [{ id: 'a1', title: 'Short' }] },
  { id: 'b', items: [] },
  {
    id: 'c',
    items: [
      {
        id: 'c1',
        title: 'A much longer headline about a thing that happened today',
      },
    ],
  },
]

describe('timeline', () => {
  it('scales dwell to reading time within bounds', () => {
    expect(dwellFor('')).toBe(4000)
    expect(
      dwellFor('one two three four five six seven eight nine ten'),
    ).toBeGreaterThan(4000)
    expect(dwellFor('word '.repeat(200))).toBe(12000)
  })

  it('builds one shot per story and one for an empty card', () => {
    const timeline = buildTimeline(cards)
    expect(timeline.shots.map((s) => s.cardId)).toEqual(['a', 'b', 'c'])
    expect(timeline.shots[1]!.itemId).toBeNull()
    expect(timeline.totalMs).toBe(
      timeline.shots.reduce((s, x) => s + x.dwellMs, 0),
    )
    expect(seekTimeline(timeline, 0)).toEqual({ index: 0, offsetMs: 0 })
    expect(seekTimeline(timeline, 4500)).toEqual({ index: 1, offsetMs: 500 })
    expect(seekTimeline(timeline, 1e9).index).toBe(2)
    expect(seekTimeline({ shots: [], totalMs: 0 }, 1).index).toBe(-1)
  })
})

describe('runner', () => {
  it('travels, holds and completes on a manual clock', () => {
    const clock = createManualClock()
    const timeline = buildTimeline(cards.slice(0, 2))
    const phases: AutoplayPhase[] = []
    const travelled: string[] = []
    const runner = createRunner({
      timeline,
      clock,
      travelMs: 100,
      travel: (shot) => travelled.push(shot.cardId),
      onChange: (s) => phases.push(s.phase),
    })
    runner.start()
    expect(runner.state().phase).toBe('travel')
    clock.advance(100)
    expect(runner.state().phase).toBe('hold')
    clock.advance(2000)
    expect(runner.state().positionMs).toBe(2000)
    clock.advance(2000)
    expect(travelled).toEqual(['a', 'b'])
    clock.advance(100 + 4000)
    expect(runner.state().phase).toBe('complete')
    expect(phases).toContain('select')
  })

  it('pauses with the remaining time and resumes', () => {
    const clock = createManualClock()
    const timeline = buildTimeline(cards.slice(0, 1))
    const runner = createRunner({ timeline, clock, travelMs: 0 })
    runner.start()
    clock.advance(1000)
    runner.pause()
    expect(runner.state().phase).toBe('paused')
    expect(runner.state().positionMs).toBe(1000)
    clock.advance(5000)
    expect(runner.state().phase).toBe('paused')
    runner.resume()
    clock.advance(2999)
    expect(runner.state().phase).toBe('hold')
    clock.advance(1)
    expect(runner.state().phase).toBe('complete')
  })

  it('seeks into a shot and stops on abort', () => {
    const clock = createManualClock()
    const timeline = buildTimeline(cards)
    const listeners = new Set<() => void>()
    const signal = {
      aborted: false,
      addEventListener: (_: 'abort', fn: () => void) => listeners.add(fn),
      removeEventListener: (_: 'abort', fn: () => void) => listeners.delete(fn),
    }
    const runner = createRunner({ timeline, clock, travelMs: 0, signal })
    runner.start(4500)
    expect(runner.state().index).toBe(1)
    clock.advance(3500)
    expect(runner.state().index).toBe(2)
    signal.aborted = true
    for (const fn of listeners) fn()
    expect(runner.state().phase).toBe('idle')
    expect(clock.pending()).toBe(0)
  })
})
