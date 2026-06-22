import type { Client } from '@polar-sh/client'
import {
  PROMOTION_TOPICS,
  promotionsApi,
  topicLabel,
  type PromotionCreate,
} from './promotions'

const makeClient = () => {
  const GET = jest.fn().mockResolvedValue({
    data: [],
    error: undefined,
    response: { status: 200 },
  })
  const POST = jest.fn().mockResolvedValue({
    data: {},
    error: undefined,
    response: { status: 200 },
  })
  const client = { GET, POST } as unknown as Client
  return { client, GET, POST }
}

const okGet = (data: unknown) => ({
  data,
  error: undefined,
  response: { status: 200 },
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

describe('promotionsApi', () => {
  it('pricing GETs the pricing endpoint', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ block_minutes: 10, price_cents: 1000 }))
    await promotionsApi(client).pricing()
    expect(GET).toHaveBeenCalledWith('/v1/promotions/pricing')
  })

  it('featured queries a single category string (not comma-joined)', async () => {
    const { client, GET } = makeClient()
    await promotionsApi(client).featured('tech')
    expect(GET).toHaveBeenCalledWith('/v1/promotions/featured', {
      params: { query: { categories: 'tech' } },
    })
  })

  it('analytics passes the days window', async () => {
    const { client, GET } = makeClient()
    GET.mockResolvedValue(okGet({ total_promotions: 0 }))
    await promotionsApi(client).analytics(7)
    expect(GET).toHaveBeenCalledWith('/v1/promotions/analytics', {
      params: { query: { days: 7 } },
    })
  })

  it('mine GETs the caller’s promotions', async () => {
    const { client, GET } = makeClient()
    await promotionsApi(client).mine()
    expect(GET).toHaveBeenCalledWith('/v1/promotions/mine')
  })

  it('create POSTs the promotion body', async () => {
    const { client, POST } = makeClient()
    POST.mockResolvedValue({
      data: { promotion_id: 'p1', url: 'https://checkout' },
      error: undefined,
      response: { status: 200 },
    })
    const body: PromotionCreate = {
      category: 'tech',
      title: 'Hello',
      body: 'World',
      blocks: 1,
    }
    await promotionsApi(client).create(body)
    expect(POST).toHaveBeenCalledWith('/v1/promotions/', { body })
  })
})
