import { WALL_THEMES, WALL_THEME_STORAGE_KEY } from '@/utils/wallTheme'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { WallThemeSwatches } from './WallThemeSwatches'

const lightRow = () =>
  Array.from(document.querySelectorAll('.swatch-row-left .swatch'))
const darkRow = () =>
  Array.from(document.querySelectorAll('.swatch-row-right .swatch'))

beforeEach(() => {
  localStorage.clear()
})
afterEach(cleanup)

describe('WallThemeSwatches', () => {
  it('offers every edition in both tones, light left and dark right', () => {
    render(<WallThemeSwatches open tone="light" onSelect={() => {}} />)

    // The point of the fan: the logo used to step a ten-stop wheel, so the
    // last look was ten clicks away. Every stop must now be reachable in one.
    expect(lightRow()).toHaveLength(WALL_THEMES.length)
    expect(darkRow()).toHaveLength(WALL_THEMES.length)
    expect(screen.getAllByRole('button')).toHaveLength(WALL_THEMES.length * 2)
  })

  it('paints each swatch the colour it applies', () => {
    render(<WallThemeSwatches open tone="light" onSelect={() => {}} />)

    // A swatch that is not its own page colour is a lie about what it does.
    // Both rows read from the SAME `chrome` map the wall and the browser
    // chrome use, so they cannot drift apart.
    const labels = (els: Element[]) =>
      els.map((el) => el.getAttribute('aria-label'))
    lightRow().forEach((el) => {
      expect((el as HTMLElement).style.backgroundColor).not.toBe('')
      expect(el.getAttribute('aria-label')).toMatch(/, light$/)
    })
    darkRow().forEach((el) => {
      expect(el.getAttribute('aria-label')).toMatch(/, dark$/)
    })
    // Every edition appears exactly once per row, whatever the order.
    const names = WALL_THEMES.map((t) => t.label).sort()
    expect(
      labels(lightRow())
        .map((l) => l!.replace(', light', ''))
        .sort(),
    ).toEqual(names)
    expect(
      labels(darkRow())
        .map((l) => l!.replace(', dark', ''))
        .sort(),
    ).toEqual(names)
  })

  it('marks exactly the edition and tone in use', () => {
    localStorage.setItem(WALL_THEME_STORAGE_KEY, 'tide')
    render(<WallThemeSwatches open tone="dark" onSelect={() => {}} />)

    const pressed = screen
      .getAllByRole('button')
      .filter((b) => b.getAttribute('aria-pressed') === 'true')
    expect(pressed).toHaveLength(1)
    expect(pressed[0]!.getAttribute('aria-label')).toBe('Tide, dark')
  })

  it('reports the edition AND the tone that was picked', async () => {
    const onSelect = vi.fn()
    render(<WallThemeSwatches open tone="light" onSelect={onSelect} />)

    // Picking a dark swatch must carry the tone with it. Sending only the
    // edition would leave a reader who clicked a dark colour on a light page.
    const idFor = (el: Element, tone: string) => {
      const label = el.getAttribute('aria-label')!.replace(`, ${tone}`, '')
      return WALL_THEMES.find((t) => t.label === label)!.id
    }
    const dark = darkRow()[1]!
    dark.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(onSelect).toHaveBeenCalledWith(idFor(dark, 'dark'), 'dark')

    const light = lightRow()[0]!
    light.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(onSelect).toHaveBeenLastCalledWith(idFor(light, 'light'), 'light')
  })

  it('follows the edition order on both sides', () => {
    render(<WallThemeSwatches open tone="light" onSelect={() => {}} />)

    // Grey, blue, purple, green, cream, nearest the mark outward, and the
    // right side mirrors it with the dark faces. Sorting by lightness was
    // tried and reshuffled the editions into an order nobody recognised, so
    // this pins the list order instead.
    const names = (els: Element[], tone: string) =>
      els.map((el) => el.getAttribute('aria-label')!.replace(`, ${tone}`, ''))
    const expected = WALL_THEMES.map((t) => t.label)
    expect(names(lightRow(), 'light')).toEqual(expected)
    expect(names(darkRow(), 'dark')).toEqual(expected)
    expect(expected[0]).toBe('Midnight')
    expect(expected[1]).toBe('Tide')
  })

  it('carries the edition accent as well as its page colour', () => {
    render(<WallThemeSwatches open tone="light" onSelect={() => {}} />)

    // One circle has to say both things: the page it paints, and the colour
    // the gem and links take with it. Page colour is the fill, accent is the
    // inner dot, and both come from the same theme entry.
    lightRow().forEach((el, i) => {
      expect(
        (el as HTMLElement).style.getPropertyValue('--swatch-accent'),
      ).toBe(WALL_THEMES[i]!.accent)
      expect(el.querySelector('.swatch-dot')).not.toBeNull()
    })
  })

  it('marks itself open so the retract has a state to animate from', () => {
    render(<WallThemeSwatches open tone="light" onSelect={() => {}} />)
    Array.from(document.querySelectorAll('.swatch-row')).forEach((row) => {
      expect(row.getAttribute('data-open')).toBe('true')
      expect(row.getAttribute('aria-hidden')).toBe('false')
    })
  })

  it('unfurls outward from the mark on both sides', () => {
    render(<WallThemeSwatches open tone="light" onSelect={() => {}} />)

    // Both rows stagger by distance from the logo, so the nearest swatch on
    // each side moves first and the fan reads as one gesture. The left row
    // reverses in CSS, so its first child is also its nearest.
    const steps = (els: Element[]) =>
      els.map((el) =>
        (el as HTMLElement).style.getPropertyValue('--swatch-step'),
      )
    const expected = WALL_THEMES.map((_, i) => String(i))
    expect(steps(lightRow())).toEqual(expected)
    expect(steps(darkRow())).toEqual(expected)
  })
})
