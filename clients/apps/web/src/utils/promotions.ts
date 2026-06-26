import { api } from '@/utils/client'
import { schemas, unwrap } from '@outception-com/client'

export type Promotion = schemas['PromotionRead']
export type PromotionPricing = schemas['PromotionPricing']
export type PromotionCheckout = schemas['PromotionCheckout']
export type PromotionCreate = schemas['PromotionCreate']
export type PromotionAnalytics = schemas['PromotionAnalytics']

export const PROMOTION_TOPICS: { id: string; label: string }[] = [
  { id: 'news', label: 'News' },
  { id: 'tech', label: 'Tech' },
  { id: 'science', label: 'Science' },
  { id: 'finance', label: 'Finance' },
  { id: 'sports', label: 'Sports' },
  { id: 'entertainment', label: 'Entertainment' },
  { id: 'gaming', label: 'Gaming' },
  { id: 'social', label: 'Social' },
  { id: 'world', label: 'World' },
]

export const topicLabel = (id: string): string =>
  PROMOTION_TOPICS.find((t) => t.id === id)?.label ?? id

/** Mirrors the backend's link/image_url validation: empty is allowed (the
 * fields are optional), otherwise the value must be an http(s) URL. Lets the
 * compose form flag a bad URL inline instead of bouncing at checkout. */
export const isOptionalHttpUrl = (value: string): boolean => {
  if (!value) return true
  try {
    const { protocol } = new URL(value)
    return protocol === 'http:' || protocol === 'https:'
  } catch {
    return false
  }
}

export const promotionsApi = {
  pricing: () => unwrap(api.GET('/v1/promotions/pricing')),
  featured: (categories: string[]) =>
    unwrap(
      api.GET('/v1/promotions/featured', {
        params: { query: { categories: categories.join(',') } },
      }),
    ),
  mine: () => unwrap(api.GET('/v1/promotions/mine')),
  analytics: (days?: number) =>
    unwrap(
      api.GET('/v1/promotions/analytics', {
        params: { query: days ? { days } : {} },
      }),
    ),
  create: (body: PromotionCreate) =>
    unwrap(api.POST('/v1/promotions/', { body })),
}

/** Click-through URL that records a click before redirecting to the promotion's
 * link. Points at the backend redirect endpoint. */
export const promotionClickUrl = (promotionId: string): string =>
  `${process.env.NEXT_PUBLIC_API_URL}/v1/promotions/${promotionId}/click`
