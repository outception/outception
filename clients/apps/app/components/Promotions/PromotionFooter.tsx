import { Box } from '@/components/Shared/Box'
import { Pill } from '@/components/Shared/Pill'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { topicLabel, useTopicPromotion } from '@/hooks/polar/promotions'
import { Linking } from 'react-native'

const SERVER_URL =
  process.env.EXPO_PUBLIC_POLAR_SERVER_URL ?? 'https://api.polar.sh'

/** The paid promotion for a card's topic, pinned at the bottom. Clicks go
 * through the backend redirect so they're counted for analytics. */
export const PromotionFooter = ({ topic }: { topic: string | null }) => {
  const { data: promotion } = useTopicPromotion(topic)

  if (!promotion) {
    return null
  }

  const onPress = () => {
    if (promotion.link) {
      Linking.openURL(`${SERVER_URL}/v1/promotions/${promotion.id}/click`)
    }
  }

  return (
    <Touchable onPress={onPress} disabled={!promotion.link}>
      <Box
        gap="spacing-4"
        padding="spacing-12"
        borderRadius="border-radius-12"
        backgroundColor="secondary"
      >
        <Box flexDirection="row" alignItems="center" gap="spacing-8">
          <Pill color="blue">Promoted</Pill>
          <Text variant="caption" color="subtext">
            {topicLabel(promotion.category)}
          </Text>
        </Box>
        <Text variant="bodyMedium">{promotion.title}</Text>
        <Text variant="caption" color="subtext">
          {promotion.body}
        </Text>
      </Box>
    </Touchable>
  )
}
