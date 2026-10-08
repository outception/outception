import type { CrawlerPageData } from '@/lib/seo/crawler'
import { safeExternalHref, timeAgo } from '@outception-com/news-core'
import { Button } from '@outception-com/orbit/Button'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'

/** A crawler page: the headlines as the wall shows them, rendered on the
 * server, with links to the publishers and one way onto the wall. */
export const CrawlerPage = ({
  data,
  labels,
}: {
  data: CrawlerPageData
  labels: {
    open: string
    openCard: string
    updated: string
    more: string | null
  }
}) => (
  <Box justifyContent="center" paddingHorizontal="l" paddingVertical="3xl">
    <Box
      as="article"
      flexDirection="column"
      rowGap="xl"
      maxWidth={720}
      width="100%"
    >
      <Box flexDirection="column" rowGap="s">
        <Text variant="heading-m" as="h1" serif>
          {data.title}
        </Text>
        <Text color="muted">{data.intro}</Text>
      </Box>
      {data.cards.map((card) => (
        <Box as="section" key={card.id} flexDirection="column" rowGap="s">
          <Box
            flexDirection="row"
            alignItems="baseline"
            justifyContent="between"
            columnGap="m"
          >
            <Text variant="heading-xs" as="h2" serif>
              {card.name}
            </Text>
            {card.updatedAt ? (
              <Text variant="caption" color="muted" as="span">
                {labels.updated} {timeAgo(card.updatedAt, undefined, 'en')}
              </Text>
            ) : null}
          </Box>
          <Box as="ol" flexDirection="column" rowGap="xs">
            {card.items.map((item) => (
              <Box as="li" key={item.id} display="block">
                <a
                  href={safeExternalHref(item.url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="headline-link"
                >
                  <Text as="span" serif>
                    {item.title}
                  </Text>
                </a>
              </Box>
            ))}
          </Box>
          <Link
            href={`/?card=${encodeURIComponent(card.id)}`}
            className="headline-link"
          >
            <Text variant="caption" as="span">
              {labels.openCard}
            </Text>
          </Link>
        </Box>
      ))}
      {labels.more ? <Text color="muted">{labels.more}</Text> : null}
      <Box
        flexDirection="column"
        alignItems="center"
        rowGap="m"
        borderRadius="l"
        backgroundColor="background-card"
        borderWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
        padding="xl"
      >
        <Link href={data.wallPath}>
          <Button>{labels.open}</Button>
        </Link>
      </Box>
    </Box>
  </Box>
)
