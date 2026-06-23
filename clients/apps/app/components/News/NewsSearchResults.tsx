import { Box } from '@/components/Shared/Box'
import { Pill } from '@/components/Shared/Pill'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useNewsSearch } from '@/hooks/polar/news'
import { openExternalUrl } from '@/utils/news'
import { ActivityIndicator, ScrollView } from 'react-native'

export const NewsSearchResults = ({ query }: { query: string }) => {
  const theme = useTheme()
  const { data, isLoading } = useNewsSearch(query)

  if (isLoading) {
    return (
      <Box flex={1} justifyContent="center" alignItems="center">
        <ActivityIndicator />
      </Box>
    )
  }

  const sources = data?.sources ?? []
  const items = data?.items ?? []

  if (sources.length === 0 && items.length === 0) {
    return (
      <Box padding="spacing-16">
        <Text variant="caption" color="subtext">
          No results for “{query}”. Headline search only covers sources the feed
          has recently shown.
        </Text>
      </Box>
    )
  }

  return (
    <ScrollView
      contentContainerStyle={{
        gap: theme.spacing['spacing-16'],
        padding: theme.spacing['spacing-16'],
      }}
    >
      {sources.length > 0 ? (
        <Box gap="spacing-8">
          <Text variant="bodyMedium">Sources</Text>
          <Box flexDirection="row" flexWrap="wrap" gap="spacing-8">
            {sources.map((s) => (
              <Touchable key={s.id} onPress={() => openExternalUrl(s.home)}>
                <Pill color="gray">{s.name}</Pill>
              </Touchable>
            ))}
          </Box>
        </Box>
      ) : null}

      {items.length > 0 ? (
        <Box gap="spacing-8">
          <Text variant="bodyMedium">Headlines</Text>
          {items.map((hit, i) => (
            <Touchable
              key={`${hit.sourceId}-${i}`}
              onPress={() => openExternalUrl(hit.item.url)}
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
        </Box>
      ) : null}
    </ScrollView>
  )
}
