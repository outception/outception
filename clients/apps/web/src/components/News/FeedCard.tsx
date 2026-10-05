'use client'

import { useCard } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import { flagOn, launchesPath } from '@outception-com/news-core'
import type { NewsItem } from '@/utils/news'
import {
  collapseStories,
  hideRead,
  isCountryCardId,
  isFeedCard,
  isMuted,
  stateFromFetch,
} from '@outception-com/news-core'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { StoreBadges } from '@/components/Landing/StoreBadges'
import type { CardProps } from './Card'
import { CardHeader } from './CardHeader'
import { FollowButton } from './FollowButton'
import { useHeadlineMenu } from './HeadlineMenu'
import { NewsListHot, NewsListTimeline } from './NewsCardList'
import { useNewsColumn } from './NewsColumnContext'
import { ShareButton } from './ShareButton'
import { WeatherStrip } from './WeatherStrip'
import {
  getMutedWords,
  getMutedWordsServerSnapshot,
  subscribeMutedWords,
} from './mutedWords'
import { FLAGS, useFlags, useReadItems } from './readerStores'
import { useClipPartialRows } from './useClipPartialRows'

const MAX_ITEMS = 30
const PRODUCTS_CARD_ID = 'products-of-the-day'

/**
 * A feed card: the publisher's headlines as a ranked list ("hottest") or a
 * timeline ("realtime"), under the shared header. Fills its parent's height
 * so the swipe deck can size it, and renders bare: the SwipeCard wrapper
 * owns the paper.
 */
export const FeedCard = ({
  card,
  active = true,
  upcoming = false,
  why,
  storyId,
}: CardProps) => {
  const { markFailed, markLoaded } = useNewsColumn()
  const t = useT()
  // The card behind is a sliver behind a mask and already holds the data it
  // fetched while it was on top, so it stays idle. The card ahead does
  // fetch: its feed can need an upstream pull, and starting that on arrival
  // is what makes a swipe land on a skeleton. Sticky, so swiping back is
  // instant.
  const [hasBeenActive, setHasBeenActive] = useState(active)
  if (active && !hasBeenActive) setHasBeenActive(true)
  const { data, isLoading, isError, errorUpdateCount, dataUpdatedAt } = useCard(
    card.id,
    'feed',
    { active, enabled: active || upcoming || hasBeenActive },
  )
  const source = card.meta ?? data?.meta ?? null
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWordsServerSnapshot,
  )
  const payloadItems = data && isFeedCard(data) ? data.payload.items : undefined
  const flags = useFlags()
  const hidingRead = flagOn(flags, FLAGS.hideRead)
  const everyOutlet = flagOn(flags, FLAGS.showEveryOutlet)
  const readItems = useReadItems()
  // Memoised: every swipe re-renders all mounted cards (their depth changes),
  // and a fresh array here would re-render every headline row with them.
  const items = useMemo(() => {
    let rows = (payloadItems ?? []).filter(
      (it) => !isMuted(it.title, mutedWords),
    )
    if (!everyOutlet) rows = collapseStories(rows)
    if (hidingRead) rows = hideRead(rows, new Set(readItems))
    return rows.slice(0, MAX_ITEMS)
  }, [payloadItems, mutedWords, everyOutlet, hidingRead, readItems])
  const { menuElement, openMenu } = useHeadlineMenu()
  const name = source?.name ?? card.id
  const onItemMenu = useCallback(
    (e: React.MouseEvent, item: NewsItem) =>
      openMenu(e, item, { id: card.id, name }),
    [openMenu, card.id, name],
  )
  const listRef = useRef<HTMLDivElement>(null)
  useClipPartialRows(listRef)

  // A feed that keeps failing is dropped from the deck so dead cards never
  // show. Keyed on the query's own poll counters, not on `isError`: once a
  // card has served data, `data` stays defined and the status never flips
  // back, so an `[isError, data]` effect would fire once and stick at one
  // strike. A 200 carrying zero rows counts as a failure too.
  const isEmpty = Boolean(data) && (payloadItems?.length ?? 0) === 0
  useEffect(() => {
    if (isError || isEmpty) markFailed(card.id)
    else if (data) markLoaded(card.id)
  }, [
    isError,
    isEmpty,
    data,
    errorUpdateCount,
    dataUpdatedAt,
    card.id,
    markFailed,
    markLoaded,
  ])

  const state =
    data?.state ??
    stateFromFetch({ loading: isLoading, error: isError, hasData: !!data })
  const hasStrip =
    active && (isCountryCardId(card.id) || source?.column === 'cities')

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      height="100%"
      padding={{ base: 'l', md: 'xl' }}
    >
      <CardHeader
        id={card.id}
        name={name}
        color={source?.color}
        logo={source?.logo}
        home={source?.home}
        updatedAt={data?.updatedAt}
        state={state}
        loading={isLoading}
        error={isError}
        why={why}
        actions={
          <>
            <ShareButton cardId={card.id} name={name} />
            <FollowButton sourceId={card.id} />
          </>
        }
      />
      {hasStrip ? <WeatherStrip attachedTo={card.id} /> : null}

      <Box flex={1} minHeight={0} overflow="hidden">
        {/* A hairline under the header, dissolving to the right, separates
            the card body. (Plain div with utility classes: the edition-ink
            fade isn't expressible as Box tokens.) The row-clip hook measures
            this div: its first child is the headline list itself. */}
        <div ref={listRef} className="rule-corner min-w-0 flex-1">
          {isLoading ? (
            /* Shimmering headline-shaped placeholders instead of a spinner:
               the card keeps its editorial silhouette while loading. */
            <Box flexDirection="column" rowGap="l" width="100%" paddingTop="s">
              {[0, 1, 2].map((i) => (
                <Box key={i} flexDirection="column" rowGap="s" width="100%">
                  <div className="skeleton-bar h-2 w-16 animate-pulse" />
                  <div className="skeleton-bar h-3.5 w-full animate-pulse" />
                  {i === 0 ? (
                    <div className="skeleton-bar h-3.5 w-2/3 animate-pulse" />
                  ) : null}
                </Box>
              ))}
            </Box>
          ) : items.length === 0 ? (
            <Text color="muted" variant="caption">
              {t('news.card.noHeadlines')}
            </Text>
          ) : source?.type === 'realtime' ? (
            <NewsListTimeline
              items={items}
              sourceName={name}
              onItemMenu={onItemMenu}
              storyId={storyId}
            />
          ) : (
            <NewsListHot
              items={items}
              sourceName={name}
              onItemMenu={onItemMenu}
              storyId={storyId}
            />
          )}
        </div>
      </Box>
      {card.id === PRODUCTS_CARD_ID ? (
        <Box
          flexDirection="row"
          alignItems="center"
          columnGap="s"
          flexWrap="wrap"
        >
          <Text variant="caption" color="muted" as="span">
            {t('news.products.house')}
          </Text>
          <Link href={`${launchesPath()}/new`} className="headline-link">
            <Text variant="caption" as="span">
              {t('news.products.submit')}
            </Text>
          </Link>
        </Box>
      ) : (
        <StoreBadges />
      )}
      {menuElement}
    </Box>
  )
}
