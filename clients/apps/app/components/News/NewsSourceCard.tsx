import { Box } from '@/components/Shared/Box'
import { Image } from '@/components/Shared/Image/Image'
import { PlaceholderBox } from '@/components/Shared/PlaceholderBox'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useNewsSource, type NewsSourceMeta } from '@/hooks/outception/news'
import { useLocale, useT } from '@/providers/LocaleProvider'
import { markFailed } from '@/utils/failedSources'
import { openExternalUrl, sourceIconUrl, timeAgo } from '@/utils/news'
import { useEffect, useState } from 'react'
import { FollowButton } from './FollowButton'
import { ShareButton } from './ShareButton'
import { NewsListHot, NewsListTimeline } from './NewsCardList'
import { KICKER_STYLE } from './newsStyles'
import { SourceAccentTab } from './SourceAccentTab'

const MAX_ITEMS = 14

/** Re-renders the consumer once a minute so relative timestamps stay
 * truthful while the screen stays mounted (the card's query has a 5-minute
 * staleTime and no refetch interval, so data alone won't re-render it). */
const useMinuteNow = () => {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000)
    return () => clearInterval(id)
  }, [])
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
 * feed drops it. */
export const NewsSourceCard = ({ source }: { source: NewsSourceMeta }) => {
  const { data, isLoading, isError } = useNewsSource(source.id)
  const items = (data?.items ?? []).slice(0, MAX_ITEMS)
  const now = useMinuteNow()
  const t = useT()
  const locale = useLocale()

  useEffect(() => {
    if (isError) markFailed(source.id)
  }, [isError, source.id])

  return (
    <Box
      flex={1}
      gap="spacing-12"
      padding="spacing-16"
      borderRadius="border-radius-16"
      backgroundColor="card"
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
            <Box
              width={32}
              height={32}
              borderRadius="border-radius-999"
              backgroundColor="background"
              style={{ overflow: 'hidden' }}
            >
              <Image
                source={sourceIconUrl(source.id)}
                style={{ width: '100%', height: '100%' }}
              />
            </Box>
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
              <Text variant="title" numberOfLines={1} style={{ flexShrink: 1 }}>
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

      <Box flex={1} style={{ overflow: 'hidden' }}>
        {isLoading ? (
          <CardSkeleton />
        ) : items.length === 0 ? (
          <Text variant="caption" color="subtext">
            {t('news.card.noHeadlines')}
          </Text>
        ) : source.type === 'hottest' ? (
          <NewsListHot items={items} />
        ) : (
          <NewsListTimeline items={items} now={now} />
        )}
      </Box>
    </Box>
  )
}
