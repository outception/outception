import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let reduced = false
vi.mock('@/utils/motion', async () => {
  const core = await import('@outception-com/news-core')
  const registry = core.createHoldRegistry()
  registry.setVisible(true)
  return { holds: registry, usePrefersReducedMotion: () => reduced }
})

import { holds } from '@/utils/motion'
import { ChartRace, type RaceInstance } from './ChartRace'
import type { RaceRow } from './race'

// Three days of page visits: /a leads, then /b overtakes it.
const rows: RaceRow[] = [
  { date: '2026-10-01', name: '/a', value: 1 },
  { date: '2026-10-02', name: '/a', value: 2 },
  { date: '2026-10-02', name: '/b', value: 1 },
  { date: '2026-10-03', name: '/a', value: 2 },
  { date: '2026-10-03', name: '/b', value: 5 },
]

const when = () => document.querySelector('.chart-race-when')?.textContent
const order = () =>
  [...document.querySelectorAll<HTMLElement>('.chart-race-row')]
    .filter((row) => row.style.opacity === '1')
    .sort(
      (a, b) =>
        Number(/translateY\((\d+)/.exec(a.style.transform)?.[1]) -
        Number(/translateY\((\d+)/.exec(b.style.transform)?.[1]),
    )
    .map((row) => row.querySelector('.chart-race-label')?.textContent)
// Each frame schedules the next after it renders: step the clock a frame
// at a time, letting React render in between.
const run = async (frames: number) => {
  for (let i = 0; i < frames; i++) {
    await act(async () => {
      vi.advanceTimersByTime(650)
    })
  }
}

describe('ChartRace', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    reduced = false
    holds.setReducedMotion(false)
    holds.setVisible(true)
  })
  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('plays the days once, reorders the bars and stops on the last', async () => {
    render(<ChartRace rows={rows} mode="visits" size="panel" />)
    await act(async () => {})
    expect(when()).toBe('1 Oct')
    expect(holds.owners()).toContain('chart-race')
    await run(1)
    expect(when()).toBe('2 Oct')
    expect(order()).toEqual(['/a', '/b'])
    await run(1)
    expect(when()).toBe('3 Oct')
    expect(order()).toEqual(['/b', '/a'])
    await run(3)
    // Finished: still on the last day, and the hold is given back.
    expect(when()).toBe('3 Oct')
    expect(holds.owners()).not.toContain('chart-race')
  })

  it('adds the days up when racing products', async () => {
    reduced = true
    render(
      <ChartRace
        rows={[
          { date: '2026-10-01', name: 'Widget', value: 2 },
          { date: '2026-10-02', name: 'Widget', value: 3 },
        ]}
        mode="products"
        size="panel"
      />,
    )
    await act(async () => {})
    expect(document.querySelector('.chart-race-value')?.textContent).toBe('5')
  })

  it('shows the last frame at once and never moves under reduced motion', async () => {
    reduced = true
    render(<ChartRace rows={rows} mode="visits" size="panel" />)
    await act(async () => {})
    expect(when()).toBe('3 Oct')
    expect(order()).toEqual(['/b', '/a'])
    expect(holds.owners()).not.toContain('chart-race')
  })

  it('pauses with the page and resumes when it returns', async () => {
    render(<ChartRace rows={rows} mode="visits" size="panel" />)
    await act(async () => {})
    await act(async () => {
      holds.setVisible(false)
    })
    await run(3)
    expect(when()).toBe('1 Oct')
    await act(async () => {
      holds.setVisible(true)
    })
    await run(1)
    expect(when()).toBe('2 Oct')
  })

  it('writes names as text and uses display labels', async () => {
    render(
      <ChartRace
        rows={[
          { date: '2026-10-01', name: '<b>x</b>', value: 2 },
          { date: '2026-10-01', name: 'views', value: 1 },
        ]}
        mode="reach"
        size="panel"
        labels={{ views: 'Views' }}
      />,
    )
    await act(async () => {})
    expect(screen.getByText('<b>x</b>')).toBeTruthy()
    expect(document.querySelector('.chart-race b')).toBeNull()
    expect(screen.getByText('Views')).toBeTruthy()
  })

  it('hands the card a play control that replays a finished race', async () => {
    let instance: RaceInstance | null = null
    const playing: boolean[] = []
    render(
      <ChartRace
        rows={rows}
        mode="visits"
        size="panel"
        onInstance={(next) => {
          instance = next
        }}
        onPlaying={(next) => playing.push(next)}
      />,
    )
    await run(5)
    expect(when()).toBe('3 Oct')
    expect(playing.at(-1)).toBe(false)
    await act(async () => {
      instance?.play()
    })
    expect(when()).toBe('1 Oct')
    expect(playing.at(-1)).toBe(true)
    await act(async () => {
      instance?.pause()
    })
    expect(playing.at(-1)).toBe(false)
  })
})
