import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({ currentUser: undefined as unknown }))
vi.mock('@/hooks/auth', () => ({ useAuth: () => auth }))
vi.mock('next/navigation', () => ({ usePathname: () => '/' }))

import { NewsColumnProvider } from './NewsColumnContext'
import { NewsNavTabs } from './NewsNavTabs'

const tabs = () =>
  render(
    <NewsColumnProvider>
      <NewsNavTabs />
    </NewsColumnProvider>,
  )

describe('NewsNavTabs account door', () => {
  afterEach(() => {
    cleanup()
    auth.currentUser = undefined
  })

  it('offers sign-in to a signed-out reader', () => {
    tabs()
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeTruthy()
  })

  it('shows the avatar at once and opens the menu once it loads', async () => {
    auth.currentUser = { email: 'reader@example.com', avatar_url: null }
    tabs()
    // The trigger paints before the menu's chunk arrives.
    expect(screen.getByRole('button', { name: 'Your account' })).toBeTruthy()
    const trigger = await screen.findByRole('button', {
      name: 'Your account',
      expanded: false,
    })
    fireEvent.keyDown(trigger, { key: 'Enter' })
    expect(await screen.findByText('Preferences')).toBeTruthy()
    expect(screen.queryByText('Review queue')).toBeNull()
  })
})
