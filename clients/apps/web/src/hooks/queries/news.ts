import { getQueryClient } from '@/utils/api/query'
import { newsApi, type NewsSort } from '@/utils/news'
import { useMutation, useQuery } from '@tanstack/react-query'
import { defaultRetry } from './retry'

export const useDefaultDeck = (enabled = true) =>
  useQuery({
    queryKey: ['news', 'default-deck'],
    queryFn: () => newsApi.defaultDeck(),
    enabled,
    staleTime: 300_000,
    retry: defaultRetry,
  })

export const useFollowedSources = (enabled = true) =>
  useQuery({
    queryKey: ['news', 'followed'],
    queryFn: () => newsApi.followed(),
    enabled,
    retry: defaultRetry,
  })

export const useFollowedFeed = (enabled = true) =>
  useQuery({
    queryKey: ['news', 'followed', 'feed'],
    queryFn: () => newsApi.followedFeed(),
    enabled,
    staleTime: 60_000,
    retry: defaultRetry,
  })

const invalidateFollowed = () =>
  getQueryClient().invalidateQueries({ queryKey: ['news', 'followed'] })

export const useFollowSource = () =>
  useMutation({
    mutationFn: (id: string) => newsApi.follow(id),
    onSuccess: invalidateFollowed,
  })

export const useUnfollowSource = () =>
  useMutation({
    mutationFn: (id: string) => newsApi.unfollow(id),
    onSuccess: invalidateFollowed,
  })

export const useNewsSources = () =>
  useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi.sources(),
    staleTime: Infinity,
    retry: defaultRetry,
  })

export const useNewsSource = (id: string | null, sort: NewsSort = 'hot') =>
  useQuery({
    queryKey: ['news', 'source', id, sort],
    queryFn: () => newsApi.source(id as string, false, sort),
    enabled: !!id,
    staleTime: 5 * 60_000,
    retry: defaultRetry,
  })

export const useNewsSearch = (query: string) =>
  useQuery({
    queryKey: ['news', 'search', query],
    queryFn: () => newsApi.search(query),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
    retry: defaultRetry,
  })

export const useNewsBatch = (sources: string[]) =>
  useQuery({
    queryKey: ['news', 'batch', [...sources].sort()],
    queryFn: () => newsApi.batch(sources),
    enabled: sources.length > 0,
    staleTime: 5 * 60_000,
    retry: defaultRetry,
  })
