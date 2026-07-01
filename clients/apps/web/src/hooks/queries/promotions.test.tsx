import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const featured = vi.fn()
const mine = vi.fn()
const analytics = vi.fn()

vi.mock('@/utils/promotions', () => ({
  promotionsApi: {
    featured: (...args: unknown[]) => featured(...args),
    mine: (...args: unknown[]) => mine(...args),
    analytics: (...args: unknown[]) => analytics(...args),
    pricing: vi.fn(),
    create: vi.fn(),
  },
}))

import {
  useMyPromotions,
  usePromotionAnalytics,
  useTopicPromotion,
} from './promotions'

const makeWrapper = () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  Wrapper.displayName = 'TestQueryWrapper'
  return Wrapper
}

beforeEach(() => {
  featured.mockReset()
  mine.mockReset()
  analytics.mockReset()
})

describe('useTopicPromotion', () => {
  it('stays idle and does not fetch when the topic is null', () => {
    const { result } = renderHook(() => useTopicPromotion(null), {
      wrapper: makeWrapper(),
    })
    expect(result.current.fetchStatus).toBe('idle')
    expect(featured).not.toHaveBeenCalled()
  })

  it('resolves to the first featured promotion for the topic', async () => {
    featured.mockResolvedValue([{ id: 'p1' }, { id: 'p2' }])
    const { result } = renderHook(() => useTopicPromotion('tech'), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(featured).toHaveBeenCalledWith(['tech'])
    expect(result.current.data).toEqual({ id: 'p1' })
  })

  it('resolves to null when the topic has no featured promotion', async () => {
    featured.mockResolvedValue([])
    const { result } = renderHook(() => useTopicPromotion('tech'), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeNull()
  })
})

describe('useMyPromotions', () => {
  it('does not fetch when disabled', () => {
    const { result } = renderHook(() => useMyPromotions(false), {
      wrapper: makeWrapper(),
    })
    expect(result.current.fetchStatus).toBe('idle')
    expect(mine).not.toHaveBeenCalled()
  })

  it('fetches the caller’s promotions when enabled', async () => {
    mine.mockResolvedValue([{ id: 'p1' }])
    const { result } = renderHook(() => useMyPromotions(true), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual([{ id: 'p1' }])
  })
})

describe('usePromotionAnalytics', () => {
  it('passes the days window through to the api', async () => {
    analytics.mockResolvedValue({ total_promotions: 0 })
    const { result } = renderHook(() => usePromotionAnalytics(7), {
      wrapper: makeWrapper(),
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(analytics).toHaveBeenCalledWith(7)
  })
})
