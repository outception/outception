'use client'

import { useLocale } from '@/providers/locale'
import { safeExternalHref, type NewsItem } from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'

/** Source-supplied trailing metadata: a short string or a small icon. */
const ExtraInfo = ({ item }: { item: NewsItem }) => {
  if (item.extra?.info) return item.extra.info
  // The icon URL comes straight from an untrusted external feed, so restrict it
  // to http(s) before using it as an image source (same guard as the links) —
  // otherwise a feed can force an outbound request to an attacker host.
  const iconSrc = item.extra?.icon
    ? safeExternalHref(item.extra.icon)
    : undefined
  if (iconSrc) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={iconSrc}
        alt=""
        className="-mt-1 inline h-4"
        referrerPolicy="no-referrer"
        onError={(e) => (e.currentTarget.style.display = 'none')}
      />
    )
  }
  return null
}

/** Ranked list for "hottest" sources — numbered rows separated by hairline
 * rules. The top story runs at hero scale in the display face; the rest stay
 * numbered. */
export const NewsListHot = ({ items }: { items: NewsItem[] }) => (
  <Box as="ol" flexDirection="column" rowGap="xs">
    {items.map((item, i) => (
      <Box as="li" key={`${item.id}-${i}`}>
        {i === 0 ? (
          <a
            href={safeExternalHref(item.url)}
            target="_blank"
            rel="noopener noreferrer"
            title={item.extra?.hover ?? undefined}
            className="headline-link rule-row block min-w-0 rounded-md pr-1 pb-2"
          >
            <Text variant="heading-xxs" as="span" serif truncate={3}>
              {item.title}{' '}
              <Text variant="caption" color="muted" as="span">
                <ExtraInfo item={item} />
              </Text>
            </Text>
          </a>
        ) : (
          <a
            href={safeExternalHref(item.url)}
            target="_blank"
            rel="noopener noreferrer"
            title={item.extra?.hover ?? undefined}
            className="headline-link rule-row flex min-w-0 items-stretch gap-2 rounded-md pr-1"
          >
            {/* Bare tabular numeral in the margin — no chip background.
                (Plain span: the muted ink mix isn't a Box token.) */}
            <span className="rank-numeral">{i + 1}</span>
            <Box
              as="span"
              display="block"
              minWidth={0}
              flexGrow={1}
              flexBasis={0}
            >
              <Text variant="body" as="span" serif truncate={2}>
                {item.title}{' '}
                <Text variant="caption" color="muted" as="span">
                  <ExtraInfo item={item} />
                </Text>
              </Text>
            </Box>
          </a>
        )}
      </Box>
    ))}
  </Box>
)

/** Timeline list for "realtime" sources — each row a tight timestamp +
 * headline cluster, with air between rows. */
export const NewsListTimeline = ({ items }: { items: NewsItem[] }) => {
  const locale = useLocale()
  return (
    <Box as="ol" flexDirection="column" rowGap="m">
      {items.map((item, i) => (
        <Box
          as="li"
          key={`${item.id}-${i}`}
          display="flex"
          flexDirection="column"
          rowGap="xs"
        >
          <Box
            as="span"
            display="inline-flex"
            alignItems="center"
            columnGap="xs"
          >
            {/* Uppercase micro-kicker timestamp (plain span: letterspaced
              uppercase micro type isn't a Text variant). */}
            <span className="meta-kicker">
              {typeof item.pubDate === 'number' ? (
                <OutceptionTimeAgo
                  date={new Date(item.pubDate)}
                  locale={locale}
                />
              ) : typeof item.extra?.date === 'number' ? (
                <OutceptionTimeAgo
                  date={new Date(item.extra.date)}
                  locale={locale}
                />
              ) : (
                (item.extra?.date ?? null)
              )}
            </span>
            <Text variant="caption" color="muted" as="span">
              <ExtraInfo item={item} />
            </Text>
          </Box>
          <a
            href={safeExternalHref(item.url)}
            target="_blank"
            rel="noopener noreferrer"
            title={item.extra?.hover ?? undefined}
            className={
              i === 0
                ? 'headline-link block rounded-md px-1 pb-1'
                : 'headline-link rounded-md px-1'
            }
          >
            <Text
              variant={i === 0 ? 'heading-xxs' : 'body'}
              as="span"
              serif
              truncate={i === 0 ? 3 : 2}
            >
              {item.title}
            </Text>
          </a>
        </Box>
      ))}
    </Box>
  )
}
