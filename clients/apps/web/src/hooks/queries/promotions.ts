import { getQueryClient } from '@/utils/api/query'
import { promotionsApi, type PromotionCreate } from '@/utils/promotions'
import { useMutation, useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

const PROMO_REFETCH_MS = 60_000

export const usePromotionPricing = () =>
  useQuery({
    queryKey: ['promotions', 'pricing'],
    queryFn: () => promotionsApi.pricing(),
    staleTime: Infinity,
    retry: defaultRetry,
  })

export const useTopicPromotion = (topic: string | null) =>
  useQuery({
    queryKey: ['promotions', 'featured', topic],
    queryFn: async () => {
      if (!topic) return null
      const featured = await promotionsApi.featured([topic])
      return featured[0] ?? null
    },
    enabled: !!topic,
    refetchInterval: PROMO_REFETCH_MS,
    retry: defaultRetry,
  })

export const useMyPromotions = (enabled = true) =>
  useQuery({
    queryKey: ['promotions', 'mine'],
    queryFn: () => promotionsApi.mine(),
    enabled,
    retry: defaultRetry,
  })

export const usePromotionAnalytics = (days = 30) =>
  useQuery({
    queryKey: ['promotions', 'analytics', days],
    queryFn: () => promotionsApi.analytics(days),
    retry: defaultRetry,
  })

export const useCreatePromotion = () =>
  useMutation({
    mutationFn: (body: PromotionCreate) => promotionsApi.create(body),
    onSuccess: () => {
      getQueryClient().invalidateQueries({ queryKey: ['promotions', 'mine'] })
    },
  })
