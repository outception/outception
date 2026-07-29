import { Box } from '@/components/Shared/Box'
import { PlaceholderBox } from '@/components/Shared/PlaceholderBox'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useNewsSource, type NewsSourceMeta } from '@/hooks/outception/news'
import { useIsRestoring } from '@tanstack/react-query'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { useTheme } from '@/design-system/useTheme'
import { LinearGradient } from 'expo-linear-gradient'
import { markFailed, markLoaded } from '@/utils/failedSources'
import { openExternalUrl, timeAgo } from '@/utils/news'
import { memo, useEffect, useState, useSyncExternalStore } from 'react'
import { FollowButton } from './FollowButton'
import { ShareButton } from './ShareButton'
import { NewsListHot, NewsListTimeline } from './NewsCardList'
import { showHeadlineActions } from './headlineActions'
import { getMutedWords, isMuted, subscribeMutedWords } from '@/utils/mutedWords'
import { useClipPartialRows } from './useClipPartialRows'
import { KICKER_STYLE } from './newsStyles'
import { SourceAccentTab } from './SourceAccentTab'
import { SourceBadge } from './SourceBadge'

const MAX_ITEMS = 30

/** Re-renders the consumer once a minute so relative timestamps stay
 * truthful while the screen stays mounted. Only ticks while `enabled` — the
 * peeking cards' timestamps are occluded behind the top card, so re-rendering
 * their whole subtree per minute bought nothing. On promotion the baseline
 * resets so a card that sat as a peek doesn't show stale labels. */
const useMinuteNow = (enabled: boolean) => {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!enabled) return
    setNow(Date.now())
    const id = setInterval(() => setNow(Date.now()), 60_000)
    return () => clearInterval(id)
  }, [enabled])
  return now
}

/** Shimmering headline-shaped placeholders — the card keeps its editorial
 * silhouette while loading (mirrors the web card's skeleton). */
const CardSkeleton = () => {
  const t = useT()
  return (
    <Box
      gap="spacing-12"
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={t('news.mobile.loadingHeadlines')}
    >
      {[0, 1, 2].map((i) => (
        <Box key={i} gap="spacing-4">
          <PlaceholderBox width={64} height={8} />
          <PlaceholderBox height={13} />
          {i === 0 ? <PlaceholderBox width="66%" height={13} /> : null}
        </Box>
      ))}
    </Box>
  )
}

/** One news source: its latest headlines (ranked "hot" list or "realtime"
 * timeline by source type), its icon + last-updated time in the header.
 * Mirrors the web card. A source whose feed errors is marked failed so the
 * feed drops it.
 *
 * Memoized: the deck re-renders on every follow toggle / failed-source update
 * behind the Sources dialog, but `source` keeps its identity (it's an element
 * of the sources query data), so the three mounted card subtrees — 15+ rows of
 * shaped serif text each — must not re-render along with it. */
export const NewsSourceCard = memo(function NewsSourceCard({
  source,
  elevated,
}: {
  source: NewsSourceMeta
  elevated?: boolean
}) {
  const { data, isLoading, isError, errorUpdateCount, dataUpdatedAt } =
    useNewsSource(source.id, elevated)
  // While the persisted cache restores on cold launch, queries are paused
  // (pending but not fetching), so isLoading is false with no data yet — which
  // would flash the empty "no headlines" card. Treat restoring-without-data as
  // loading so the skeleton shows until the cached wall paints.
  const isRestoring = useIsRestoring()
  const mutedWords = useSyncExternalStore(
    subscribeMutedWords,
    getMutedWords,
    getMutedWords,
  )
  const items = (data?.items ?? [])
    .filter((it) => !isMuted(it.title, mutedWords))
    .slice(0, MAX_ITEMS)
  const onItemLongPress = (item: (typeof items)[number]) =>
    showHeadlineActions(item, source, items)
  const now = useMinuteNow(Boolean(elevated))
  const t = useT()
  const theme = useTheme()
  // Gap matches NewsCardList: spacing-4 for the hot list, spacing-12 for the
  // timeline — the clip must subtract it or the last row still gets sliced.
  const clip = useClipPartialRows(
    items.length,
    source.type === 'hottest'
      ? theme.spacing['spacing-4']
      : theme.spacing['spacing-12'],
  )
  const locale = useLocale()

  // Keyed on the query's poll counters, not on `isError`: once a source has
  // served data, `data` stays defined and the status never flips back to
  // pending, so an `[isError]` effect fires once and the strike count sticks at
  // 1. A 200 carrying zero headlines is a failure too — the backend caches
  // empty results, so such a source would never error and never be dropped.
  const isEmpty = Boolean(data) && (data?.items?.length ?? 0) === 0
  useEffect(() => {
    if (isError || isEmpty) markFailed(source.id)
    else if (data) markLoaded(source.id)
  }, [isError, isEmpty, data, errorUpdateCount, dataUpdatedAt, source.id])

  return (
    <Box
      flex={1}
      gap="spacing-12"
      padding="spacing-16"
      borderRadius="border-radius-16"
      backgroundColor={elevated ? 'card' : 'cardUnder'}
      borderWidth={1}
      borderColor="border"
      // Paper-sheet depth, mirroring the web card: a hairline ring + a soft
      // offset drop shadow so the card reads as a sheet resting on the pile.
      // `elevation` is the Android half — without it the card renders flat
      // there. It's safe alongside the deck's zIndex because it runs the same
      // direction: the front card (zIndex 30) also gets the highest elevation,
      // so the two agree on stacking instead of fighting.
      style={
        // Only the top card gets the drop shadow; peeks keep just the hairline
        // ring (mirrors the web, where peeking neighbours are ring-only).
        // shadowColor defaults to black in RN — unset to satisfy no-hardcoded-colors.
        elevated
          ? {
              shadowOffset: {
                width: 0,
                height: theme.dimension['dimension-12'],
              },
              shadowOpacity: 0.18,
              shadowRadius: theme.dimension['dimension-24'],
              elevation: 8,
            }
          : { elevation: 1 }
      }
    >
      {/* Section color-coding: the source's accent as a short rounded tab
          hanging from the card's top-left edge (matches the web sheet). */}
      <SourceAccentTab color={source.color} />
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="space-between"
        gap="spacing-8"
      >
        <Box
          flexDirection="row"
          alignItems="center"
          gap="spacing-8"
          flexShrink={1}
        >
          <Touchable onPress={() => openExternalUrl(source.home ?? undefined)}>
            <SourceBadge
              id={source.id}
              name={source.name}
              logo={source.logo}
              size={32}
            />
          </Touchable>
          <Box gap="spacing-2" flexShrink={1}>
            <Box flexDirection="row" alignItems="center" gap="spacing-8">
              <Box
                width={8}
                height={8}
                borderRadius="border-radius-999"
                flexShrink={0}
                style={{ backgroundColor: source.color }}
              />
              <Text
                variant="bodySerif"
                numberOfLines={1}
                style={{ flexShrink: 1 }}
              >
                {source.name}
              </Text>
            </Box>
            <Text variant="caption" color="subtext" style={KICKER_STYLE}>
              {data?.updatedTime
                ? `${t('news.card.updated')} ${timeAgo(data.updatedTime, now, locale)}`
                : isError
                  ? t('news.card.failed')
                  : t('news.card.loading')}
            </Text>
          </Box>
        </Box>
        <Box flexDirection="row" alignItems="center" gap="spacing-8">
          <ShareButton source={source} />
          <FollowButton sourceId={source.id} />
        </Box>
      </Box>

      {/* The card doesn't scroll, so the list is clipped by overflow. `clip`
          drops any row that wouldn't fit whole, so the cut never lands
          mid-sentence — the RN equivalent of the web's useClipPartialRows. */}
      {/* Web draws `.rule-corner` under the header — a hairline that DISSOLVES
          to the right (solid to 40%, gone by 92%) plus 10px of air — so
          headlines never butt straight into the badge row. */}
      <Box
        flex={1}
        paddingTop="spacing-10"
        style={{ overflow: 'hidden', position: 'relative' }}
        onLayout={clip.onContainerLayout}
      >
        <LinearGradient
          // `border` is always an opaque #rrggbb (see editions.mix), so the
          // fade end is the same hue at 0 alpha — 'transparent' would fringe
          // grey on iOS by interpolating through transparent black.
          colors={[
            theme.colors.border,
            theme.colors.border,
            `${theme.colors.border}00`,
          ]}
          locations={[0, 0.4, 0.92]}
          start={{ x: 0, y: 0.5 }}
          end={{ x: 1, y: 0.5 }}
          pointerEvents="none"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: theme.dimension['dimension-1'],
          }}
        />
        {isLoading || (isRestoring && !data) ? (
          <CardSkeleton />
        ) : items.length === 0 ? (
          <Text variant="caption" color="subtext">
            {t('news.card.noHeadlines')}
          </Text>
        ) : source.type === 'hottest' ? (
          <NewsListHot
            items={items}
            clip={clip}
            onItemLongPress={onItemLongPress}
          />
        ) : (
          <NewsListTimeline
            items={items}
            now={now}
            clip={clip}
            onItemLongPress={onItemLongPress}
          />
        )}
      </Box>
    </Box>
  )
})
