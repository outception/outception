import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import { useLocale } from '@/providers/LocaleProvider'
import { openExternalUrl, timeAgo, type NewsItem } from '@/utils/news'
import { KICKER_STYLE } from './newsStyles'

/** Ranked list for "hottest" sources — the top story runs large, the rest are
 * numbered rows separated by hairlines. Mirrors the web NewsListHot. */
export const NewsListHot = ({ items }: { items: NewsItem[] }) => {
  const theme = useTheme()
  return (
    <Box gap="spacing-8">
      {items.map((item, i) => (
        <Touchable
          key={`${item.id}-${i}`}
          onPress={() => openExternalUrl(item.url)}
        >
          {i === 0 ? (
            <Box paddingBottom="spacing-8">
              <Text variant="subtitle" numberOfLines={3}>
                {item.title}
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
                style={{ minWidth: theme.dimension['dimension-16'] }}
              >
                {i + 1}
              </Text>
              <Box flex={1}>
                <Text variant="body" numberOfLines={2}>
                  {item.title}
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
}: {
  items: NewsItem[]
  now: number
}) => {
  const locale = useLocale()
  return (
    <Box gap="spacing-12">
      {items.map((item, i) => (
        <Touchable
          key={`${item.id}-${i}`}
          onPress={() => openExternalUrl(item.url)}
        >
          <Box gap="spacing-2">
            {typeof item.pubDate === 'number' ? (
              <Text variant="caption" color="subtext" style={KICKER_STYLE}>
                {timeAgo(item.pubDate, now, locale)}
              </Text>
            ) : null}
            <Text
              variant={i === 0 ? 'subtitle' : 'body'}
              numberOfLines={i === 0 ? 3 : 2}
            >
              {item.title}
            </Text>
          </Box>
        </Touchable>
      ))}
    </Box>
  )
}
