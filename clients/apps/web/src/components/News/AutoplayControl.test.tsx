import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRef } from 'react'

vi.mock('@/utils/motion', async () => {
  const core = await import('@outception-com/news-core')
  const registry = core.createHoldRegistry()
  registry.setVisible(true)
  return { holds: registry, usePrefersReducedMotion: () => false }
})

import { AutoplayControl } from './AutoplayControl'

describe('AutoplayControl', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('plays through the cards and stops on interaction', () => {
    const goTo = vi.fn()
    const deck = document.createElement('div')
    document.body.appendChild(deck)
    const ref = createRef<HTMLElement>()
    ref.current = deck
    render(
      <AutoplayControl
        cardIds={['a', 'b', 'c']}
        index={0}
        goTo={goTo}
        interactionRef={ref}
      />,
    )
    fireEvent.click(screen.getByRole('button'))
    expect(goTo).toHaveBeenLastCalledWith(0)
    act(() => {
      vi.advanceTimersByTime(500 + 8000)
    })
    expect(goTo).toHaveBeenLastCalledWith(1)
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('true')
    fireEvent.pointerDown(deck)
    act(() => {
      vi.advanceTimersByTime(20_000)
    })
    expect(goTo).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe(
      'false',
    )
  })
})
