'use client'

import { useTopicPromotion } from '@/hooks/queries/promotions'
import { promotionClickUrl } from '@/utils/promotions'
import { Box } from '@outception-com/orbit/Box'

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
      alignItems="end"
      padding="s"
      borderRadius="l"
      backgroundColor="background-card"
      textAlign="right"
    >
      <span className="line-clamp-1 text-xs font-medium text-black dark:text-white">
        {promotion.title}
      </span>
      <span className="line-clamp-1 text-xs text-gray-500 dark:text-neutral-400">
        {promotion.body}
      </span>
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
