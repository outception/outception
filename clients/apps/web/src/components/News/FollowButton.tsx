'use client'

import { useT } from '@/providers/locale'
import { Button } from '@outception-com/orbit'
import { useNewsColumn } from './NewsColumnContext'

/** Star a source into your device-local deck ("Your deck"). No login needed. */
export const FollowButton = ({ sourceId }: { sourceId: string }) => {
  const { isFocused, toggleFocus } = useNewsColumn()
  const t = useT()
  const followed = isFocused(sourceId)

  return (
    <Button
      variant={followed ? 'secondary' : 'ghost'}
      size="sm"
      onClick={() => toggleFocus(sourceId)}
    >
      {followed ? t('news.follow.following') : t('news.follow.follow')}
    </Button>
  )
}
