import { describe, expect, it } from 'vitest'
import { createHoldRegistry } from './holds'

describe('holds', () => {
  it('animates only with a hold, a visible tab and no reduced motion', () => {
    const registry = createHoldRegistry()
    expect(registry.shouldAnimate()).toBe(false)
    const release = registry.take('ticker')
    expect(registry.shouldAnimate()).toBe(true)
    expect(registry.shouldAnimate('ticker')).toBe(true)
    expect(registry.shouldAnimate('flap')).toBe(false)
    expect(registry.shouldAnimate('ticker', false)).toBe(false)
    registry.setVisible(false)
    expect(registry.shouldAnimate()).toBe(false)
    registry.setVisible(true)
    registry.setReducedMotion(true)
    expect(registry.shouldAnimate()).toBe(false)
    registry.setReducedMotion(false)
    release()
    release()
    expect(registry.count()).toBe(0)
    expect(registry.shouldAnimate()).toBe(false)
  })

  it('counts holds per owner and notifies', () => {
    const registry = createHoldRegistry()
    let n = 0
    registry.subscribe(() => {
      n += 1
    })
    const a = registry.take('x')
    const b = registry.take('x')
    expect(registry.count()).toBe(2)
    expect(registry.owners()).toEqual(['x'])
    a()
    expect(registry.shouldAnimate('x')).toBe(true)
    b()
    expect(n).toBe(4)
  })
})
