import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
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
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['promotions', 'pricing'],
    queryFn: () => promotionsApi(outception).pricing(),
    staleTime: Infinity,
  })
}

export const useTopicPromotion = (topic: string | null) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['promotions', 'featured', topic],
    queryFn: async () => {
      if (!topic) return null
      const featured = await promotionsApi(outception).featured(topic)
      return featured[0] ?? null
    },
    enabled: !!topic,
    refetchInterval: 60_000,
  })
}

export const useMyPromotions = (enabled = true) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['promotions', 'mine'],
    queryFn: () => promotionsApi(outception).mine(),
    enabled,
  })
}

export const usePromotionAnalytics = (days = 30) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['promotions', 'analytics', days],
    queryFn: () => promotionsApi(outception).analytics(days),
  })
}

export const useCreatePromotion = () => {
  const { outception } = useOutceptionClient()
  return useMutation({
    mutationFn: (body: PromotionCreate) =>
      promotionsApi(outception).create(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promotions', 'mine'] })
    },
  })
}

export const usePromotionPreferences = () => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['promotions', 'preferences'],
    queryFn: () => promotionsApi(outception).preferences(),
  })
}

export const useUpdatePromotionPreferences = () => {
  const { outception } = useOutceptionClient()
  return useMutation({
    mutationFn: (enabled: boolean) =>
      promotionsApi(outception).updatePreferences(enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['promotions', 'preferences'] })
    },
  })
}
