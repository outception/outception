'use client'

import { safeExternalHref, type NewsItem } from '@/utils/news'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'

/** Source-supplied trailing metadata: a short string or a small icon. */
const ExtraInfo = ({ item }: { item: NewsItem }) => {
  if (item.extra?.info) return item.extra.info
  if (item.extra?.icon) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={item.extra.icon}
        alt=""
        className="-mt-1 inline h-4"
        referrerPolicy="no-referrer"
        onError={(e) => (e.currentTarget.style.display = 'none')}
      />
    )
  }
  return null
}

/** Ranked list for "hottest" sources — numbered rows. */
export const NewsListHot = ({ items }: { items: NewsItem[] }) => (
  <Box as="ol" flexDirection="column" rowGap="xs">
    {items.map((item, i) => (
      <Box as="li" key={`${item.id}-${i}`}>
        <a
          href={safeExternalHref(item.url)}
          target="_blank"
          rel="noopener noreferrer"
          title={item.extra?.hover ?? undefined}
          className="flex min-w-0 items-stretch gap-2 rounded-md pr-1 transition-colors hover:bg-neutral-400/10"
        >
          <Box
            as="span"
            display="inline-flex"
            minWidth={24}
            alignItems="center"
            justifyContent="center"
            borderRadius="s"
            backgroundColor="background-card"
          >
            <Text variant="caption">{i + 1}</Text>
          </Box>
          <Box
            as="span"
            display="block"
            minWidth={0}
            flexGrow={1}
            flexBasis={0}
          >
            <Text variant="body" as="span">
              {item.title}{' '}
              <Text variant="caption" color="muted" as="span">
                <ExtraInfo item={item} />
              </Text>
            </Text>
          </Box>
        </a>
      </Box>
    ))}
  </Box>
)

/** Timeline list for "realtime" sources — timestamped rows. */
export const NewsListTimeline = ({ items }: { items: NewsItem[] }) => (
  <Box
    as="ol"
    flexDirection="column"
    rowGap="s"
    marginLeft="xs"
    paddingLeft="s"
    borderLeftWidth={1}
    borderStyle="solid"
    borderColor="border-secondary"
  >
    {items.map((item, i) => (
      <Box
        as="li"
        key={`${item.id}-${i}`}
        display="flex"
        flexDirection="column"
        rowGap="xs"
      >
        <Box as="span" display="inline-flex" alignItems="center" columnGap="xs">
          <Text variant="caption" color="muted" as="span">
            {typeof item.pubDate === 'number' ? (
              <OutceptionTimeAgo date={new Date(item.pubDate)} />
            ) : typeof item.extra?.date === 'number' ? (
              <OutceptionTimeAgo date={new Date(item.extra.date)} />
            ) : (
              (item.extra?.date ?? null)
            )}
          </Text>
          <Text variant="caption" color="muted" as="span">
            <ExtraInfo item={item} />
          </Text>
        </Box>
        <a
          href={safeExternalHref(item.url)}
          target="_blank"
          rel="noopener noreferrer"
          title={item.extra?.hover ?? undefined}
          className="rounded-md px-1 transition-colors hover:bg-neutral-400/10"
        >
          <Text variant="body" as="span">
            {item.title}
          </Text>
        </a>
      </Box>
    ))}
  </Box>
)
