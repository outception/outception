import { beforeEach, describe, expect, it, vi, type Mock } from 'vitest'

vi.mock('@/utils/client', () => ({
  api: { GET: vi.fn(), POST: vi.fn() },
}))

import { api } from '@/utils/client'
import type { PromotionCreate } from './promotions'
import {
  PROMOTION_TOPICS,
  promotionClickUrl,
  promotionsApi,
  topicLabel,
} from './promotions'

const ok = (data: unknown) => ({
  data,
  error: undefined,
  response: { ok: true, status: 200, headers: new Headers() },
})

const get = api.GET as unknown as Mock
const post = api.POST as unknown as Mock

beforeEach(() => {
  get.mockReset()
  post.mockReset()
  get.mockResolvedValue(ok([]))
  post.mockResolvedValue(ok({}))
})

describe('topicLabel', () => {
  it('maps a known topic id to its label', () => {
    expect(topicLabel('tech')).toBe('Tech')
    expect(topicLabel('world')).toBe('World')
  })

  it('falls back to the raw id for an unknown topic', () => {
    expect(topicLabel('not-a-topic')).toBe('not-a-topic')
  })
})

describe('PROMOTION_TOPICS', () => {
  it('has unique ids and includes the core topics', () => {
    const ids = PROMOTION_TOPICS.map((t) => t.id)
    expect(new Set(ids).size).toBe(ids.length)
    expect(ids).toContain('news')
    expect(ids).toContain('tech')
  })

  it('gives every topic a non-empty label', () => {
    for (const topic of PROMOTION_TOPICS) {
      expect(topic.label.length).toBeGreaterThan(0)
    }
  })
})

describe('promotionClickUrl', () => {
  it('builds the backend redirect URL from NEXT_PUBLIC_API_URL', () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.example')
    expect(promotionClickUrl('abc')).toBe(
      'https://api.example/v1/promotions/abc/click',
    )
    vi.unstubAllEnvs()
  })
})

describe('promotionsApi', () => {
  it('pricing GETs the pricing endpoint', async () => {
    get.mockResolvedValue(ok({ block_minutes: 10, price_cents: 1000 }))
    await promotionsApi.pricing()
    expect(get).toHaveBeenCalledWith('/v1/promotions/pricing')
  })

  it('featured joins the categories into a comma-separated query', async () => {
    await promotionsApi.featured(['news', 'tech', 'science'])
    expect(get).toHaveBeenCalledWith('/v1/promotions/featured', {
      params: { query: { categories: 'news,tech,science' } },
    })
  })

  it('analytics includes the days window only when provided', async () => {
    await promotionsApi.analytics(7)
    expect(get).toHaveBeenLastCalledWith('/v1/promotions/analytics', {
      params: { query: { days: 7 } },
    })

    await promotionsApi.analytics()
    expect(get).toHaveBeenLastCalledWith('/v1/promotions/analytics', {
      params: { query: {} },
    })
  })

  it('mine GETs the caller’s promotions', async () => {
    await promotionsApi.mine()
    expect(get).toHaveBeenCalledWith('/v1/promotions/mine')
  })

  it('create POSTs the promotion body', async () => {
    post.mockResolvedValue(ok({ promotion_id: 'p1', url: 'https://checkout' }))
    const body: PromotionCreate = {
      category: 'tech',
      title: 'Hello',
      body: 'World',
      blocks: 1,
    }
    await promotionsApi.create(body)
    expect(post).toHaveBeenCalledWith('/v1/promotions/', { body })
  })
})
