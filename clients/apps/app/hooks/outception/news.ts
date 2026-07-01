import { useOutceptionClient } from '@/providers/OutceptionClientProvider'
import { newsApi, type NewsSort } from '@/utils/news'
import { queryClient } from '@/utils/query'
import { useMutation, useQuery } from '@tanstack/react-query'

export type {
  NewsItem,
  NewsSearchResult,
  NewsSort,
  NewsSourceMeta,
  NewsSourceResponse,
} from '@/utils/news'

export const useNewsSearch = (query: string) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'search', query],
    queryFn: () => newsApi(outception).search(query),
    enabled: query.trim().length >= 2,
    staleTime: 30_000,
  })
}

export const useFollowedSources = (enabled = true) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'followed'],
    queryFn: () => newsApi(outception).followed(),
    enabled,
  })
}

export const useFollowedFeed = (enabled = true) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'followed', 'feed'],
    queryFn: () => newsApi(outception).followedFeed(),
    enabled,
    staleTime: 60_000,
  })
}

export const useFollowSource = () => {
  const { outception } = useOutceptionClient()
  return useMutation({
    mutationFn: (id: string) => newsApi(outception).follow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['news', 'followed'] })
    },
  })
}

export const useUnfollowSource = () => {
  const { outception } = useOutceptionClient()
  return useMutation({
    mutationFn: (id: string) => newsApi(outception).unfollow(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['news', 'followed'] })
    },
  })
}

export const useNewsSources = () => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'sources'],
    queryFn: () => newsApi(outception).sources(),
    staleTime: Infinity,
  })
}

export const useNewsSource = (
  id: string | undefined,
  sort: NewsSort = 'hot',
) => {
  const { outception } = useOutceptionClient()
  return useQuery({
    queryKey: ['news', 'source', id, sort],
    queryFn: () => newsApi(outception).source(id ?? '', sort),
    enabled: !!id,
    staleTime: 5 * 60_000,
  })
}
