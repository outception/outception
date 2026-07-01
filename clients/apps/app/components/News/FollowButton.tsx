import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import {
  useFollowSource,
  useFollowedSources,
  useUnfollowSource,
} from '@/hooks/outception/news'
import { useSession } from '@/providers/SessionProvider'

export const FollowButton = ({ sourceId }: { sourceId: string }) => {
  const { session } = useSession()
  const { data } = useFollowedSources(!!session)
  const follow = useFollowSource()
  const unfollow = useUnfollowSource()

  if (!session) return null

  const isFollowing = (data?.sourceIds ?? []).includes(sourceId)

  return (
    <Touchable
      onPress={() =>
        isFollowing ? unfollow.mutate(sourceId) : follow.mutate(sourceId)
      }
    >
      <Box
        paddingVertical="spacing-4"
        paddingHorizontal="spacing-8"
        borderRadius="border-radius-999"
        backgroundColor={isFollowing ? 'primary' : 'border'}
      >
        <Text
          variant="caption"
          color={isFollowing ? 'monochromeInverted' : 'subtext'}
        >
          {isFollowing ? '★ Following' : '☆ Follow'}
        </Text>
      </Box>
    </Touchable>
  )
}
