'use client'

import { useTopicPromotion } from '@/hooks/queries/promotions'
import { promotionClickUrl } from '@/utils/promotions'

/**
 * The paid "in focus" promotion for a card's topic, pinned inside the news card
 * at the bottom. Renders nothing when the topic has no active promotion. Clicks
 * go through the backend redirect so they're counted for analytics.
 *
 * Uses the `glass-panel` frosted surface (not a solid fill) so it reads as glass
 * like the rest of the wall — see the glass design language in globals.css.
 */
export const PromotionFooter = ({ topic }: { topic: string | null }) => {
  const { data: promotion } = useTopicPromotion(topic)

  if (!promotion) {
    return null
  }

  const body = (
    <div className="glass-panel flex w-full flex-col items-end gap-1 rounded-2xl px-3 py-2 text-right">
      <span className="line-clamp-1 text-xs font-medium text-black dark:text-white">
        {promotion.title}
      </span>
      <span className="line-clamp-1 text-xs text-gray-500 dark:text-neutral-400">
        {promotion.body}
      </span>
    </div>
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
