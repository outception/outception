'use client'

import { useNewsSource } from '@/hooks/queries/news'
import { useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { Pill, Spinner, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import { useEffect, useRef } from 'react'
import { FollowButton } from './FollowButton'
import { NewsListHot, NewsListTimeline } from './NewsCardList'
import { useClipPartialRows } from './useClipPartialRows'
import { useNewsColumn } from './NewsColumnContext'

const MAX_ITEMS = 30

/**
 * One panel on the wall: the source's headlines rendered as a ranked list
 * ("hottest" sources) or a timeline ("realtime" sources), with the source's
 * accent dot, icon and last-updated time in the header, and the paid promotion
 * for the source's topic pinned at the bottom. Fills its parent's height so the
 * swipe deck can size it.
 *
 * Renders bare (no own surface): the draggable SwipeDeckCard wrapper owns the
 * glass — a denser veil on the front card, a lighter rim on the peeking
 * neighbours — so the content here sits directly on that.
 */
export const NewsSourceCard = ({ source }: { source: NewsSourceMeta }) => {
  const { data, isLoading, isError } = useNewsSource(source.id)
  const { markFailed } = useNewsColumn()
  const t = useT()
  const items = (data?.items ?? []).slice(0, MAX_ITEMS)
  const iconKey = source.id.split('-')[0]
  const listRef = useRef<HTMLDivElement>(null)
  useClipPartialRows(listRef)

  // A source whose feed errors is dropped from the deck (see NewsWall) so dead
  // cards never show — mirroring the original's failed-source filter.
  useEffect(() => {
    if (isError) markFailed(source.id)
  }, [isError, source.id, markFailed])

  return (
    <Box flexDirection="column" rowGap="m" height="100%" padding="l">
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="between"
        columnGap="s"
      >
        <Box flexDirection="row" alignItems="center" columnGap="s">
          <a
            href={source.home ?? undefined}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={source.name}
            style={{
              height: 32,
              width: 32,
              borderRadius: 9999,
              backgroundSize: 'cover',
              backgroundImage: `url(/news-icons/${iconKey}.png)`,
            }}
          />
          <Box flexDirection="column" rowGap="none">
            <Box flexDirection="row" alignItems="center" columnGap="s">
              <span
                aria-hidden
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  borderRadius: 9999,
                  backgroundColor: source.color,
                }}
              />
              <Text variant="body" as="h3">
                {source.name}
              </Text>
              {source.title ? <Pill color="gray">{source.title}</Pill> : null}
            </Box>
            <Text variant="caption" color="muted">
              {data?.updatedTime ? (
                <>
                  {t('news.card.updated')}{' '}
                  <OutceptionTimeAgo date={new Date(data.updatedTime)} />
                </>
              ) : isError ? (
                t('news.card.failed')
              ) : (
                t('news.card.loading')
              )}
            </Text>
          </Box>
        </Box>
        <FollowButton sourceId={source.id} />
      </Box>

      <Box ref={listRef} flex={1} minHeight={0} overflow="hidden">
        {isLoading ? (
          <Box justifyContent="center" padding="l">
            <Spinner />
          </Box>
        ) : items.length === 0 ? (
          <Text color="muted" variant="caption">
            {t('news.card.noHeadlines')}
          </Text>
        ) : source.type === 'hottest' ? (
          <NewsListHot items={items} />
        ) : (
          <NewsListTimeline items={items} />
        )}
      </Box>
    </Box>
  )
}

export default NewsSourceCard
