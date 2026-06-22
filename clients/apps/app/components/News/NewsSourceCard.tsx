import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useNewsSource, type NewsSourceMeta } from '@/hooks/polar/news'
import { ActivityIndicator, Linking } from 'react-native'
import { PromotionFooter } from '../Promotions/PromotionFooter'

const MAX_ITEMS = 6

/** One news source: its latest headlines plus the paid promotion (if any) for
 * the source's topic. */
export const NewsSourceCard = ({ source }: { source: NewsSourceMeta }) => {
  const { data, isLoading } = useNewsSource(source.id)
  const items = (data?.items ?? []).slice(0, MAX_ITEMS)

  return (
    <Box
      gap="spacing-12"
      padding="spacing-16"
      borderRadius="border-radius-16"
      backgroundColor="card"
    >
      <Box flexDirection="row" alignItems="center" gap="spacing-8">
        <Box
          width={10}
          height={10}
          borderRadius="border-radius-999"
          style={{ backgroundColor: source.color }}
        />
        <Text variant="title">{source.name}</Text>
      </Box>

      {isLoading ? (
        <ActivityIndicator />
      ) : items.length === 0 ? (
        <Text variant="caption" color="subtext">
          No headlines right now.
        </Text>
      ) : (
        <Box gap="spacing-8">
          {items.map((item) => (
            <Touchable key={item.id} onPress={() => Linking.openURL(item.url)}>
              <Text variant="body">{item.title}</Text>
            </Touchable>
          ))}
        </Box>
      )}

      <PromotionFooter topic={source.column ?? null} />
    </Box>
  )
}
