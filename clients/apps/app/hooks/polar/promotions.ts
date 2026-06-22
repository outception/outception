import { usePolarClient } from '@/providers/PolarClientProvider'
import { queryClient } from '@/utils/query'
import { schemas, unwrap } from '@polar-sh/client'
import { useMutation, useQuery } from '@tanstack/react-query'

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

export const usePromotionPricing = () => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['promotions', 'pricing'],
    queryFn: () => unwrap(polar.GET('/v1/promotions/pricing')),
    staleTime: Infinity,
  })
}

export const useTopicPromotion = (topic: string | null) => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['promotions', 'featured', topic],
    queryFn: async () => {
      if (!topic) return null
      const featured = await unwrap(
        polar.GET('/v1/promotions/featured', {
          params: { query: { categories: topic } },
        }),
      )
      return featured[0] ?? null
    },
    enabled: !!topic,
    refetchInterval: 60_000,
  })
}

export const useMyPromotions = (enabled = true) => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['promotions', 'mine'],
    queryFn: () => unwrap(polar.GET('/v1/promotions/mine')),
    enabled,
  })
}

export const usePromotionAnalytics = (days = 30) => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['promotions', 'analytics', days],
    queryFn: () =>
      unwrap(
        polar.GET('/v1/promotions/analytics', { params: { query: { days } } }),
      ),
  })
}

export const useCreatePromotion = () => {
  const { polar } = usePolarClient()
  return useMutation({
    mutationFn: (body: PromotionCreate) =>
      unwrap(polar.POST('/v1/promotions/', { body })),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promotions', 'mine'] })
    },
  })
}
