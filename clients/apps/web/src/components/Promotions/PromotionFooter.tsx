'use client'

import { useT } from '@/providers/locale'
import { useTopicPromotion } from '@/hooks/queries/promotions'
import { promotionClickUrl, topicLabel } from '@/utils/promotions'
import { Pill } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'

/**
 * The paid "in focus" promotion for a card's topic, pinned at the bottom of the
 * news card. Renders nothing when the topic has no active promotion. Clicks go
 * through the backend redirect so they're counted for analytics.
 */
export const PromotionFooter = ({ topic }: { topic: string | null }) => {
  const t = useT()
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
      <Box flexDirection="row" alignItems="center" columnGap="s">
        <Pill color="blue">{t('promotions.promoted')}</Pill>
        <span className="text-xs text-gray-500 dark:text-neutral-400">
          {topicLabel(promotion.category)}
        </span>
      </Box>
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
