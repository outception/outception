import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/mobile', () => ({ useIsMobileMedia: () => false }))

vi.mock('./SwipeCard', () => ({
  PEEK_X: 56,
  PEEK_X_MOBILE: 24,
  SwipeCard: ({ card, depth }: { card: { id: string }; depth: number }) => (
    <div data-testid={`card-${card.id}`} data-depth={depth} />
  ),
}))

import { NewsCards } from './NewsCards'

const deck = ['a', 'b', 'c'].map((id) => ({ id, kind: 'feed' as const }))

describe('NewsCards keyboard', () => {
  beforeEach(() => {
    localStorage.clear()
  })
  afterEach(cleanup)

  it('moves with the arrow keys and wraps', () => {
    render(<NewsCards cards={deck} column="test" />)
    const region = screen.getByTestId('card-deck')
    expect(screen.getByTestId('card-a').dataset.depth).toBe('0')
    fireEvent.keyDown(region, { key: 'ArrowRight' })
    expect(screen.getByTestId('card-b').dataset.depth).toBe('0')
    fireEvent.keyDown(region, { key: 'ArrowLeft' })
    fireEvent.keyDown(region, { key: 'ArrowLeft' })
    expect(screen.getByTestId('card-c').dataset.depth).toBe('0')
  })

  it('is focusable and labelled for assistive tech', () => {
    render(<NewsCards cards={deck} column="test" />)
    const region = screen.getByRole('region')
    expect(region.getAttribute('tabindex')).toBe('0')
    expect(region.getAttribute('aria-label')).toMatch(/arrow keys/)
  })
})
