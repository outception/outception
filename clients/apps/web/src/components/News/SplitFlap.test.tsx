import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let reduced = false
vi.mock('@/utils/motion', async () => {
  const core = await import('@outception-com/news-core')
  const registry = core.createHoldRegistry()
  registry.setVisible(true)
  return {
    holds: registry,
    usePrefersReducedMotion: () => reduced,
    useHoldsEnvironment: () => {},
  }
})

import { SplitFlap } from './SplitFlap'

describe('SplitFlap', () => {
  beforeEach(() => {
    reduced = false
    let now = 0
    vi.spyOn(performance, 'now').mockImplementation(() => now)
    vi.stubGlobal('requestAnimationFrame', (fn: FrameRequestCallback) => {
      now += 50
      return setTimeout(() => fn(now), 0) as unknown as number
    })
    vi.stubGlobal('cancelAnimationFrame', (id: number) => clearTimeout(id))
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('shows the text at once on first render', () => {
    render(<SplitFlap text="UPDATED 5M" owner="x" />)
    expect(screen.getByTestId('split-flap').textContent).toBe('UPDATED 5M')
  })

  it('flips through intermediate glyphs and lands on the new text', async () => {
    const { rerender } = render(<SplitFlap text="A" owner="x" />)
    rerender(<SplitFlap text="C" owner="x" />)
    await act(async () => {
      await new Promise((r) => setTimeout(r, 5))
    })
    const mid = screen.getByTestId('split-flap').textContent
    expect(['A', 'B', 'C']).toContain(mid)
    await act(async () => {
      await new Promise((r) => setTimeout(r, 60))
    })
    expect(screen.getByTestId('split-flap').textContent).toBe('C')
    expect(screen.getByTestId('split-flap').getAttribute('aria-label')).toBe(
      'C',
    )
  })

  it('does not animate under reduced motion', async () => {
    reduced = true
    const { rerender } = render(<SplitFlap text="A" owner="x" />)
    rerender(<SplitFlap text="C" owner="x" />)
    expect(screen.getByTestId('split-flap').textContent).toBe('C')
  })
})
