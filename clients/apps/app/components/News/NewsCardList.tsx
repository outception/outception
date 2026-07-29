import { Box } from '@/components/Shared/Box'
import { Image } from '@/components/Shared/Image/Image'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useLocale } from '@/providers/LocaleProvider'
import { openExternalUrl, timeAgo, type NewsItem } from '@/utils/news'
import { KICKER_STYLE } from './newsStyles'
import type { useClipPartialRows } from './useClipPartialRows'

type Clip = ReturnType<typeof useClipPartialRows>

const isHttpUrl = (url: string | null | undefined): url is string =>
  !!url && /^https?:\/\/\S+$/i.test(url)

/** The timeline timestamp for a headline: the publish time, falling through to
 * the feed's `extra.date` (number → relative, string → shown verbatim). Mirrors
 * the web timeline's timestamp fallback so realtime sources that supply their
 * time in `extra.date` still show one. */
const timelineStamp = (
  item: NewsItem,
  now: number,
  locale: string,
): string | null => {
  if (typeof item.pubDate === 'number')
    return timeAgo(item.pubDate, now, locale)
  if (typeof item.extra?.date === 'number') {
    return timeAgo(item.extra.date, now, locale)
  }
  if (typeof item.extra?.date === 'string') return item.extra.date
  return null
}

/** Source-supplied trailing metadata: a short string (e.g. Hacker News points /
 * Reddit comment counts) or a small icon. The icon URL comes from an untrusted
 * feed, so it's restricted to http(s) before use. Mirrors the web ExtraInfo. */
const ExtraInfo = ({ item }: { item: NewsItem }) => {
  const theme = useTheme()
  if (item.extra?.info) {
    return (
      <Text variant="caption" color="subtext">
        {item.extra.info}
      </Text>
    )
  }
  const icon = item.extra?.icon
  if (isHttpUrl(icon)) {
    const size = theme.dimension['dimension-16']
    return <Image source={icon} style={{ width: size, height: size }} />
  }
  return null
}

/** The trailing `info` string appended inline after a headline (the common
 * aggregator case), falling back to the icon form like the web's ExtraInfo —
 * icon-only sources otherwise show nothing where web shows the favicon. */
const InlineInfo = ({ item }: { item: NewsItem }) =>
  item.extra?.info ? (
    <Text variant="caption" color="subtext">
      {` ${item.extra.info}`}
    </Text>
  ) : isHttpUrl(item.extra?.icon) ? (
    <ExtraInfo item={item} />
  ) : null

/** Ranked list for "hottest" sources — the top story runs large, the rest are
 * numbered rows separated by hairlines. Mirrors the web NewsListHot. */
export const NewsListHot = ({
  items,
  clip,
}: {
  items: NewsItem[]
  clip: Clip
}) => {
  const theme = useTheme()
  return (
    <Box gap="spacing-4">
      {items.slice(0, clip.visibleCount).map((item, i) => (
        <Touchable
          key={`${item.id}-${i}`}
          onPress={() => openExternalUrl(item.url)}
          onLayout={clip.onRowLayout(i)}
        >
          {i === 0 ? (
            <Box paddingBottom="spacing-8">
              <Text variant="leadSerif" numberOfLines={3}>
                {item.title}
                <InlineInfo item={item} />
              </Text>
            </Box>
          ) : (
            <Box
              flexDirection="row"
              gap="spacing-8"
              alignItems="flex-start"
              paddingVertical="spacing-4"
              borderTopWidth={1}
              borderColor="border"
            >
              <Text
                variant="caption"
                color="subtext"
                style={{
                  minWidth: theme.dimension['dimension-20'],
                  textAlign: 'center',
                  paddingTop: theme.spacing['spacing-2'],
                }}
              >
                {i + 1}
              </Text>
              <Box flex={1}>
                <Text variant="bodySerif" numberOfLines={2}>
                  {item.title}
                  <InlineInfo item={item} />
                </Text>
              </Box>
            </Box>
          )}
        </Touchable>
      ))}
    </Box>
  )
}

/** Timeline list for "realtime" sources — each row a timestamp kicker above the
 * headline, with air between rows. Mirrors the web NewsListTimeline. */
export const NewsListTimeline = ({
  items,
  now,
  clip,
}: {
  items: NewsItem[]
  now: number
  clip: Clip
}) => {
  const locale = useLocale()
  return (
    <Box gap="spacing-12">
      {items.slice(0, clip.visibleCount).map((item, i) => {
        const stamp = timelineStamp(item, now, locale)
        const hasExtra = !!item.extra?.info || isHttpUrl(item.extra?.icon)
        return (
          <Touchable
            key={`${item.id}-${i}`}
            onPress={() => openExternalUrl(item.url)}
            onLayout={clip.onRowLayout(i)}
          >
            <Box gap="spacing-4">
              {stamp || hasExtra ? (
                <Box flexDirection="row" alignItems="center" gap="spacing-4">
                  {stamp ? (
                    <Text
                      variant="caption"
                      color="subtext"
                      style={KICKER_STYLE}
                    >
                      {stamp}
                    </Text>
                  ) : null}
                  <ExtraInfo item={item} />
                </Box>
              ) : null}
              {/* Web's lead row is heading-xxs (18/500 serif) — leadSerif is
                  the app's purpose-built match; `title` ran a step heavier. */}
              <Text
                variant={i === 0 ? 'leadSerif' : 'bodySerif'}
                numberOfLines={i === 0 ? 3 : 2}
              >
                {item.title}
              </Text>
            </Box>
          </Touchable>
        )
      })}
    </Box>
  )
}
