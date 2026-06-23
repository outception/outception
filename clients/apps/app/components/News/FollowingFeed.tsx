import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useFollowedFeed } from '@/hooks/polar/news'
import { ActivityIndicator, Linking, ScrollView } from 'react-native'

export const FollowingFeed = () => {
  const theme = useTheme()
  const { data, isLoading } = useFollowedFeed()

  if (isLoading) {
    return (
      <Box flex={1} justifyContent="center" alignItems="center">
        <ActivityIndicator />
      </Box>
    )
  }

  const items = data?.items ?? []

  if (items.length === 0) {
    return (
      <Box padding="spacing-16">
        <Text variant="caption" color="subtext">
          Follow some sources with the ☆ button to build your feed. New
          headlines appear here as the feed warms them.
        </Text>
      </Box>
    )
  }

  return (
    <ScrollView
      contentContainerStyle={{
        gap: theme.spacing['spacing-8'],
        padding: theme.spacing['spacing-16'],
      }}
    >
      {items.map((hit, i) => (
        <Touchable
          key={`${hit.sourceId}-${i}`}
          onPress={() => Linking.openURL(hit.item.url)}
        >
          <Box
            gap="spacing-4"
            padding="spacing-12"
            borderRadius="border-radius-16"
            backgroundColor="card"
          >
            <Text variant="body">{hit.item.title}</Text>
            <Text variant="caption" color="subtext">
              {hit.sourceName}
            </Text>
          </Box>
        </Touchable>
      ))}
    </ScrollView>
  )
}
