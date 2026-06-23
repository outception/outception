'use client'

import { useAuth } from '@/hooks'
import {
  useFollowSource,
  useFollowedSources,
  useUnfollowSource,
} from '@/hooks/queries/news'
import { Button } from '@polar-sh/orbit'

export const FollowButton = ({ sourceId }: { sourceId: string }) => {
  const { currentUser } = useAuth()
  const { data } = useFollowedSources(!!currentUser)
  const follow = useFollowSource()
  const unfollow = useUnfollowSource()

  if (!currentUser) return null

  const isFollowing = (data?.sourceIds ?? []).includes(sourceId)

  return (
    <Button
      variant={isFollowing ? 'secondary' : 'ghost'}
      size="sm"
      loading={follow.isPending || unfollow.isPending}
      onClick={() =>
        isFollowing ? unfollow.mutate(sourceId) : follow.mutate(sourceId)
      }
    >
      {isFollowing ? '★ Following' : '☆ Follow'}
    </Button>
  )
}
