import type { Client, schemas } from '@polar-sh/client'
import { unwrap } from '@polar-sh/client'

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

export const promotionsApi = (polar: Client) => ({
  pricing: () => unwrap(polar.GET('/v1/promotions/pricing')),
  featured: (topic: string) =>
    unwrap(
      polar.GET('/v1/promotions/featured', {
        params: { query: { categories: topic } },
      }),
    ),
  mine: () => unwrap(polar.GET('/v1/promotions/mine')),
  analytics: (days: number) =>
    unwrap(
      polar.GET('/v1/promotions/analytics', { params: { query: { days } } }),
    ),
  create: (body: PromotionCreate) =>
    unwrap(polar.POST('/v1/promotions/', { body })),
})
