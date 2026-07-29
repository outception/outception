'use client'

import { useLocale, useT } from '@/providers/locale'
import { memo, useCallback, useState } from 'react'
import { type NewsItem, isSummarizable, safeExternalHref } from '@/utils/news'
import { InlineSummary } from './InlineSummary'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import OutceptionTimeAgo from '@outception-com/ui/components/atoms/OutceptionTimeAgo'

/** Source-supplied trailing metadata: a short string or a small icon. */
const ExtraInfo = ({ item }: { item: NewsItem }) => {
  if (item.extra?.info) return item.extra.info
  // The icon URL comes straight from an untrusted external feed, so restrict it
  // to http(s) before using it as an image source (same guard as the links) -
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

/** Trailing "that's everything" caption for short feeds: a card that shows
 * every item it has (fewer than a full page) would otherwise just stop dead -
 * the note tells the reader nothing was cut off. */
const CaughtUpNote = ({ count }: { count: number }) => {
  const t = useT()
  if (count === 0 || count >= 12) return null
  return (
    <Box as="li" display="block">
      <Text variant="caption" color="muted" as="p">
        {t('news.caughtUp.body')}
      </Text>
    </Box>
  )
}

/** Ranked list for "hottest" sources - numbered rows separated by hairline
 * rules. The top story runs at hero scale in the display face; the rest stay
 * numbered. */
/** Plain left-clicks expand the AI summary inline under the headline;
 * modified clicks (new tab / middle click) keep the browser default, and the
 * right-click menu's "Open article" is untouched. Links that can't be
 * summarized (Google News redirects, videos) open the article directly -
 * never an "unavailable" message. */
const useInlineSummary = () => {
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  // A summary that failed (and opened the article) must collapse its row,
  // otherwise the next tap on that headline toggles an already-expanded key
  // and does nothing.
  const onSummaryClose = useCallback(() => setExpandedKey(null), [])
  const onHeadlineClick = (
    e: React.MouseEvent,
    key: string,
    item: NewsItem,
  ) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0)
      return
    if (!isSummarizable(item.url)) return
    e.preventDefault()
    setExpandedKey((current) => (current === key ? null : key))
  }
  return { expandedKey, onHeadlineClick, onSummaryClose }
}

export const NewsListHot = memo(function NewsListHot({
  items,
  sourceName,
  onItemMenu,
}: {
  items: NewsItem[]
  sourceName: string
  onItemMenu?: (e: React.MouseEvent, item: NewsItem) => void
}) {
  const { expandedKey, onHeadlineClick, onSummaryClose } = useInlineSummary()
  return (
    <Box as="ol" flexDirection="column" rowGap="xs">
      {items.map((item, i) => (
        <Box as="li" key={`${item.id}-${i}`}>
          {i === 0 ? (
            <a
              href={safeExternalHref(item.url)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => onHeadlineClick(e, `${item.id}-${i}`, item)}
              onContextMenu={
                onItemMenu ? (e) => onItemMenu(e, item) : undefined
              }
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
              onClick={(e) => onHeadlineClick(e, `${item.id}-${i}`, item)}
              onContextMenu={
                onItemMenu ? (e) => onItemMenu(e, item) : undefined
              }
              title={item.extra?.hover ?? undefined}
              className="headline-link rule-row flex min-w-0 items-stretch gap-2 rounded-md pr-1"
            >
              {/* Bare tabular numeral in the margin - no chip background.
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
          {expandedKey === `${item.id}-${i}` && (
            <InlineSummary
              url={item.url}
              sourceName={sourceName}
              onClose={onSummaryClose}
            />
          )}
        </Box>
      ))}
      <CaughtUpNote count={items.length} />
    </Box>
  )
})

/** Timeline list for "realtime" sources - each row a tight timestamp +
 * headline cluster, with air between rows. */
export const NewsListTimeline = memo(function NewsListTimeline({
  items,
  sourceName,
  onItemMenu,
}: {
  items: NewsItem[]
  sourceName: string
  onItemMenu?: (e: React.MouseEvent, item: NewsItem) => void
}) {
  const locale = useLocale()
  const { expandedKey, onHeadlineClick, onSummaryClose } = useInlineSummary()
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
                  date={item.pubDate}
                  locale={locale}
                  minPeriod={60}
                />
              ) : typeof item.extra?.date === 'number' ? (
                <OutceptionTimeAgo
                  date={item.extra.date}
                  locale={locale}
                  minPeriod={60}
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
            onClick={(e) => onHeadlineClick(e, `${item.id}-${i}`, item)}
            onContextMenu={onItemMenu ? (e) => onItemMenu(e, item) : undefined}
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
          {expandedKey === `${item.id}-${i}` && (
            <InlineSummary
              url={item.url}
              sourceName={sourceName}
              onClose={onSummaryClose}
            />
          )}
        </Box>
      ))}
      <CaughtUpNote count={items.length} />
    </Box>
  )
})
