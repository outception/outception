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

  it('plays from arrival, stops on interaction and resumes from the control', () => {
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
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('true')
  })

  it('starts on arrival and stays stopped once the reader pauses', () => {
    const goTo = vi.fn()
    const ref = createRef<HTMLElement>()
    ref.current = document.createElement('div')
    const { rerender } = render(
      <AutoplayControl
        cardIds={['a', 'b', 'c']}
        index={1}
        goTo={goTo}
        interactionRef={ref}
      />,
    )
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe('true')
    act(() => {
      vi.advanceTimersByTime(500 + 8000)
    })
    expect(goTo).toHaveBeenLastCalledWith(2)
    fireEvent.click(screen.getByRole('button'))
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe(
      'false',
    )
    // A card drops and the timeline changes: the pause holds.
    rerender(
      <AutoplayControl
        cardIds={['a', 'c']}
        index={1}
        goTo={goTo}
        interactionRef={ref}
      />,
    )
    act(() => {
      vi.advanceTimersByTime(20_000)
    })
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe(
      'false',
    )
  })

  it('does not start when motion is reduced', async () => {
    const { holds } = await import('@/utils/motion')
    holds.setReducedMotion(true)
    const ref = createRef<HTMLElement>()
    ref.current = document.createElement('div')
    render(
      <AutoplayControl
        cardIds={['a', 'b']}
        index={0}
        goTo={vi.fn()}
        interactionRef={ref}
      />,
    )
    expect(screen.getByRole('button').getAttribute('aria-pressed')).toBe(
      'false',
    )
    holds.setReducedMotion(false)
  })
})
