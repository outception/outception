'use client'

import { useTopicPromotion } from '@/hooks/queries/promotions'
import { promotionClickUrl, topicLabel } from '@/utils/promotions'
import { Pill, Text } from '@polar-sh/orbit'
import { Box } from '@polar-sh/orbit/Box'

/**
 * The paid "in focus" promotion for a card's topic, pinned at the bottom of the
 * news card. Renders nothing when the topic has no active promotion. Clicks go
 * through the backend redirect so they're counted for analytics.
 */
export const PromotionFooter = ({ topic }: { topic: string | null }) => {
  const { data: promotion } = useTopicPromotion(topic)

  if (!promotion) {
    return null
  }

  const body = (
    <Box
      flexDirection="column"
      rowGap="xs"
      padding="m"
      borderRadius="l"
      backgroundColor="background-card"
    >
      <Box flexDirection="row" alignItems="center" columnGap="s">
        <Pill color="blue">Promoted</Pill>
        <Text variant="caption" color="muted">
          {topicLabel(promotion.category)}
        </Text>
      </Box>
      <Text variant="body" as="h4">
        {promotion.title}
      </Text>
      <Text color="muted" variant="caption">
        {promotion.body}
      </Text>
    </Box>
  )

  if (!promotion.link) {
    return body
  }

  return (
    <a
      href={promotionClickUrl(promotion.id)}
      target="_blank"
      rel="noreferrer noopener"
      className="block no-underline"
    >
      {body}
    </a>
  )
}

export default PromotionFooter
