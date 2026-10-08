import { describe, expect, it } from 'vitest'
import { glyphsAt, isSettled, planFlap } from './splitFlap'

describe('splitFlap', () => {
  it('starts on from, ends on to, pads the shorter text', () => {
    const plan = planFlap('AB', 'ABCD')
    expect(glyphsAt(plan, 0)).toBe('AB  ')
    expect(glyphsAt(plan, plan.duration)).toBe('ABCD')
    expect(isSettled(plan, plan.duration)).toBe(true)
    expect(plan.columns[0]!.steps).toBe(0)
  })

  it('steps forward through the ring and staggers columns', () => {
    const plan = planFlap('A', 'C', { stepMs: 10, staggerMs: 0, maxSteps: 12 })
    expect(plan.columns[0]!.steps).toBe(2)
    expect(glyphsAt(plan, 0)).toBe('A')
    expect(glyphsAt(plan, 10)).toBe('B')
    expect(glyphsAt(plan, 20)).toBe('C')
    const staggered = planFlap('AA', 'BB', { stepMs: 10, staggerMs: 50 })
    expect(staggered.columns[1]!.start).toBe(50)
    expect(glyphsAt(staggered, 10)).toBe('BA')
  })

  it('caps long runs and lands exactly on the target', () => {
    const plan = planFlap(' ', '9', { stepMs: 10, staggerMs: 0, maxSteps: 4 })
    expect(plan.columns[0]!.steps).toBe(4)
    expect(plan.duration).toBe(40)
    expect(glyphsAt(plan, 40)).toBe('9')
  })

  it('keeps lowercase targets lowercase and jumps unknown glyphs', () => {
    const plan = planFlap('a', 'c', { stepMs: 10, staggerMs: 0 })
    expect(glyphsAt(plan, 10)).toBe('b')
    const jump = planFlap('é', 'x', { stepMs: 10, staggerMs: 0 })
    expect(jump.columns[0]!.steps).toBe(1)
    expect(glyphsAt(jump, 10)).toBe('x')
  })
})
