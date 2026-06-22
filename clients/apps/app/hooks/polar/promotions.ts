import { usePolarClient } from '@/providers/PolarClientProvider'
import { promotionsApi, type PromotionCreate } from '@/utils/promotions'
import { queryClient } from '@/utils/query'
import { useMutation, useQuery } from '@tanstack/react-query'

export { PROMOTION_TOPICS, topicLabel } from '@/utils/promotions'
export type {
  Promotion,
  PromotionAnalytics,
  PromotionCheckout,
  PromotionCreate,
  PromotionPricing,
} from '@/utils/promotions'

export const usePromotionPricing = () => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['promotions', 'pricing'],
    queryFn: () => promotionsApi(polar).pricing(),
    staleTime: Infinity,
  })
}

export const useTopicPromotion = (topic: string | null) => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['promotions', 'featured', topic],
    queryFn: async () => {
      if (!topic) return null
      const featured = await promotionsApi(polar).featured(topic)
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
    queryFn: () => promotionsApi(polar).mine(),
    enabled,
  })
}

export const usePromotionAnalytics = (days = 30) => {
  const { polar } = usePolarClient()
  return useQuery({
    queryKey: ['promotions', 'analytics', days],
    queryFn: () => promotionsApi(polar).analytics(days),
  })
}

export const useCreatePromotion = () => {
  const { polar } = usePolarClient()
  return useMutation({
    mutationFn: (body: PromotionCreate) => promotionsApi(polar).create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promotions', 'mine'] })
    },
  })
}
