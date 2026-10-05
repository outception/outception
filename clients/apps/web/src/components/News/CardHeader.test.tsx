import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { CardHeader } from './CardHeader'

describe('CardHeader', () => {
  afterEach(cleanup)

  it('shows the update time and no state word on a healthy card', () => {
    render(
      <CardHeader
        id="bbc-world"
        name="BBC"
        updatedAt={Date.now()}
        state="nominal"
      />,
    )
    expect(screen.getByRole('heading', { name: 'BBC' })).toBeTruthy()
    expect(screen.getByTestId('card-kicker').textContent).toMatch(/updated/)
    expect(screen.queryByTestId('card-state')).toBeNull()
  })

  it('adds a tertiary word for a stale card and keeps the time', () => {
    render(
      <CardHeader
        id="bbc-world"
        name="BBC"
        updatedAt={Date.now()}
        state="stale"
      />,
    )
    expect(screen.getByTestId('card-state').textContent).toMatch(/not updating/)
    expect(screen.getByTestId('card-kicker').textContent).toMatch(/updated/)
  })

  it('reads loading and failed while there is no data', () => {
    const { rerender } = render(<CardHeader id="x" name="X" loading />)
    expect(screen.getByTestId('card-kicker').textContent).toMatch(/loading/)
    rerender(<CardHeader id="x" name="X" error state="unavailable" />)
    expect(screen.getByTestId('card-kicker').textContent).toMatch(/failed/)
    expect(screen.getByTestId('card-state').textContent).toMatch(/unavailable/)
  })

  it('shows the why line and skips the badge on request', () => {
    render(
      <CardHeader
        id="briefing:x"
        name="Briefing"
        badge={false}
        why="Because"
      />,
    )
    expect(screen.getByText('Because')).toBeTruthy()
    expect(screen.queryByRole('img')).toBeNull()
  })
})
