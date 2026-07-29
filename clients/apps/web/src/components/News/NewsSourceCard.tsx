'use client'

import { useNewsSource } from '@/hooks/queries/news'
import { useLocale, useT } from '@/providers/locale'
import { safeExternalHref, type NewsSourceMeta } from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { StoreBadges } from '@/components/Landing/StoreBadges'
import { FollowButton } from './FollowButton'
import { ShareButton } from './ShareButton'
import { NewsListHot, NewsListTimeline } from './NewsCardList'
import { useHeadlineMenu } from './HeadlineMenu'
import {
  getMutedWords,
  getMutedWordsServerSnapshot,
  isMuted,
  subscribeMutedWords,
} from './mutedWords'
import { SourceBadge } from './SourceBadge'
import { useClipPartialRows } from './useClipPartialRows'
import { useNewsColumn } from './NewsColumnContext'

const MAX_ITEMS = 30

/**
 * One panel on the wall: the source's headlines rendered as a ranked list
 * ("hottest" sources) or a timeline ("realtime" sources), with the source's
 * accent dot, icon and last-updated time in the header. Fills its parent's
 * height so the swipe deck can size it.
 *
 * Renders bare (no own surface): the draggable SwipeDeckCard wrapper owns the
 * paper — the crisp front sheet on the top card, a bare rule on the peeking
 * neighbours — so the content here sits directly on that.
 */
export const NewsSourceCard = ({
  source,
  active = true,
  upcoming = false,
}: {
  source: NewsSourceMeta
  active?: boolean
  /** The card one swipe ahead: it fetches so its headlines are on screen the
   * moment it arrives, but it does not poll — only the top card does. */
  upcoming?: boolean
}) => {
  const { markFailed, markLoaded } = useNewsColumn()
  const t = useT()
  const locale = useLocale()
  // The card behind is a ~24px sliver behind a mask and already holds the data
  // it fetched while it was on top, so it stays idle. The card ahead does
  // fetch: its feed can need an upstream pull and a translation pass, and
  // starting that on arrival is what makes a swipe land on a skeleton. The flag
  // is sticky so swiping back to a card is instant.
  const [hasBeenActive, setHasBeenActive] = useState(active)
  if (active && !hasBeenActive) setHasBeenActive(true)
  // Headlines are live source text; the backend machine-translates them into
  // the reader's language as part of this fetch (cache-first, no-op for
  // English), so the card paints translated on first render — no English flash,
  // no second round trip.
  const { data, isLoading, isError, errorUpdateCount, dataUpdatedAt } =
    useNewsSource(
      source.id,
      'hot',
      locale,
      active,
      active || upcoming || hasBeenActive,
    )
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWordsServerSnapshot,
  )
  // Memoised: every swipe re-renders all mounted cards (their depth changes),
  // and a fresh array here would re-render every headline row with them.
  const items = useMemo(
    () =>
      (data?.items ?? [])
        .filter((it) => !isMuted(it.title, mutedWords))
        .slice(0, MAX_ITEMS),
    [data?.items, mutedWords],
  )
  const { menuElement, openMenu } = useHeadlineMenu(source.id, source.name)
  const listRef = useRef<HTMLDivElement>(null)
  useClipPartialRows(listRef)

  // A source that keeps failing is dropped from the deck (see NewsWall) so dead
  // cards never show. Keyed on the query's own poll counters, not on `isError`:
  // once a source has served data at least once, `data` stays defined and the
  // status never flips back to pending, so an `[isError, data]` effect fires
  // exactly once and the strike counter would stick at 1 forever.
  //
  // A 200 carrying zero headlines counts as a failure too — the card has
  // nothing to show, and the backend now caches empty results, so such a source
  // would otherwise never error and never be dropped.
  const isEmpty = Boolean(data) && (data?.items?.length ?? 0) === 0
  useEffect(() => {
    if (isError || isEmpty) markFailed(source.id)
    else if (data) markLoaded(source.id)
  }, [
    isError,
    isEmpty,
    data,
    errorUpdateCount,
    dataUpdatedAt,
    source.id,
    markFailed,
    markLoaded,
  ])

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      height="100%"
      padding={{ base: 'l', md: 'xl' }}
    >
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="between"
        columnGap="s"
      >
        <Box
          flexDirection="row"
          alignItems="center"
          columnGap="s"
          flexShrink={1}
          minWidth={0}
        >
          <a
            href={safeExternalHref(source.home)}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={source.name}
            style={{ flexShrink: 0, lineHeight: 0 }}
          >
            <SourceBadge
              id={source.id}
              name={source.name}
              logo={source.logo}
              size={32}
            />
          </a>
          <Box flexDirection="column" rowGap="none" minWidth={0}>
            <Box
              flexDirection="row"
              alignItems="center"
              columnGap="s"
              minWidth={0}
            >
              <span
                aria-hidden
                style={{
                  display: 'inline-block',
                  width: 8,
                  height: 8,
                  flexShrink: 0,
                  borderRadius: 9999,
                  backgroundColor: source.color,
                }}
              />
              <Text variant="body" as="h3" serif truncate>
                {source.name}
              </Text>
            </Box>
            {/* Uppercase micro-kicker, like the row timestamps (plain span:
                letterspaced uppercase micro type isn't a Text variant). */}
            <span className="meta-kicker">
              {data?.updatedTime ? (
                <>
                  {t('news.card.updated')}{' '}
                  <OutceptionTimeAgo
                    date={data.updatedTime}
                    locale={locale}
                    minPeriod={60}
                  />
                </>
              ) : isError ? (
                t('news.card.failed')
              ) : (
                t('news.card.loading')
              )}
            </span>
          </Box>
        </Box>
        <Box
          flexDirection="row"
          alignItems="center"
          columnGap="s"
          flexShrink={0}
        >
          <ShareButton source={source} />
          <FollowButton sourceId={source.id} />
        </Box>
      </Box>

      <Box flex={1} minHeight={0} overflow="hidden">
        {/* A hairline under the header, dissolving to the right, separates
            the card body. (Plain div with utility classes: the edition-ink
            fade isn't expressible as Box tokens, and the repo's
            no-classname-box rule forbids putting the class on the wrapper
            Box — AGENTS.md escape hatch.) The row-clip hook measures this
            div: its first child is the headline list itself. */}
        <div ref={listRef} className="rule-corner min-w-0 flex-1">
          {isLoading ? (
            /* Shimmering headline-shaped placeholders instead of a spinner —
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
          ) : source.type === 'hottest' ? (
            <NewsListHot
              items={items}
              sourceName={source.name}
              onItemMenu={openMenu}
            />
          ) : (
            <NewsListTimeline
              items={items}
              sourceName={source.name}
              onItemMenu={openMenu}
            />
          )}
        </div>
      </Box>
      {/* The card's promo slot: the app-store badges (game cards don't
          carry this — their whole body is the game). */}
      <StoreBadges />
      {menuElement}
    </Box>
  )
}
