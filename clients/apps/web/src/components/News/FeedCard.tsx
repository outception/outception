'use client'

import { useCard } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import { CONFIG } from '@/utils/config'
import { launchesPath } from '@outception-com/news-core'
import type { NewsItem } from '@/utils/news'
import {
  feedRows,
  isCountryCardId,
  isFeedCard,
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
import { TellUsSheet } from '@/components/Landing/TellUsSheet'
import { ACCOUNTS_ENABLED } from '@/utils/features'
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
import { useReadItems } from './readerStores'
import { useClipPartialRows } from './useClipPartialRows'

const MAX_ITEMS = 30
const PRODUCTS_CARD_ID = 'products-of-the-day'
/** Products already counted as viewed in this page load. */
const viewedProducts = new Set<string>()

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
  // The web has no switches for these any more: one row per story, and a
  // read headline stays in the list (it only dims), so a tap never makes
  // the row it opened disappear.
  const hidingRead = false
  const everyOutlet = false
  const readItems = useReadItems()
  // Memoised: every swipe re-renders all mounted cards (their depth changes),
  // and a fresh array here would re-render every headline row with them.
  const items = useMemo(
    () =>
      feedRows({
        items: payloadItems ?? [],
        mutedWords,
        everyOutlet,
        hidingRead,
        read: new Set(readItems),
      }).slice(0, MAX_ITEMS),
    [payloadItems, mutedWords, everyOutlet, hidingRead, readItems],
  )
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
  // The products card on top counts a view for each product it shows, once
  // per page load; the beacon ignores anything that is not listed.
  useEffect(() => {
    if (!active || card.id !== PRODUCTS_CARD_ID || !payloadItems) return
    const ids = payloadItems
      .map((item) => item.id)
      .filter((id) => id.startsWith('launch-') && !viewedProducts.has(id))
      .slice(0, 10)
    if (ids.length === 0) return
    for (const id of ids) viewedProducts.add(id)
    // A plain keepalive fetch: the shared client would queue a network-error
    // toast for a dropped beacon, which nobody should see.
    void fetch(`${CONFIG.BASE_URL}/v1/launches/views`, {
      method: 'POST',
      keepalive: true,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        ids: ids.map((id) => id.slice('launch-'.length)),
      }),
    }).catch(() => {})
  }, [active, card.id, payloadItems])
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
          alignItems="baseline"
          columnGap="s"
          flexWrap="wrap"
        >
          <Text variant="caption" color="muted" as="span">
            {t('news.products.house')}
          </Text>
          {ACCOUNTS_ENABLED ? (
            <Link href={`${launchesPath()}/new`} className="headline-link">
              <Text variant="caption" as="span">
                {t('news.products.submit')}
              </Text>
            </Link>
          ) : (
            <TellUsSheet kind="launch" trigger="headline" />
          )}
        </Box>
      ) : (
        <StoreBadges />
      )}
      {menuElement}
    </Box>
  )
}
