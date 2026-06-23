'use client'

import { useNewsSource } from '@/hooks/queries/news'
import { safeExternalHref, type NewsSourceMeta } from '@/utils/news'
import { Spinner, Text } from '@polar-sh/orbit'
import { Box } from '@polar-sh/orbit/Box'
import { PromotionFooter } from '../Promotions/PromotionFooter'
import { FollowButton } from './FollowButton'

const MAX_ITEMS = 8

/**
 * One news source rendered as a card: the source's latest headlines plus the
 * paid promotion (if any) for the source's topic, pinned at the bottom.
 */
export const NewsSourceCard = ({ source }: { source: NewsSourceMeta }) => {
  const { data, isLoading } = useNewsSource(source.id)
  const items = (data?.items ?? []).slice(0, MAX_ITEMS)

  return (
    <Box
      flexDirection="column"
      rowGap="m"
      padding="l"
      borderRadius="l"
      backgroundColor="background-card"
    >
      <Box
        flexDirection="row"
        alignItems="center"
        justifyContent="between"
        columnGap="s"
      >
        <Box flexDirection="row" alignItems="center" columnGap="s">
          <span
            aria-hidden
            style={{
              display: 'inline-block',
              width: 10,
              height: 10,
              borderRadius: 9999,
              backgroundColor: source.color,
            }}
          />
          <Text variant="body" as="h3">
            {source.name}
          </Text>
        </Box>
        <FollowButton sourceId={source.id} />
      </Box>

      {isLoading ? (
        <Box justifyContent="center" padding="l">
          <Spinner />
        </Box>
      ) : items.length === 0 ? (
        <Text color="muted" variant="caption">
          No headlines right now.
        </Text>
      ) : (
        <Box as="ul" flexDirection="column" rowGap="s">
          {items.map((item) => (
            <Box as="li" key={item.id}>
              <a
                href={safeExternalHref(item.url)}
                target="_blank"
                rel="noreferrer noopener"
                className="hover:text-blue-500"
              >
                <Text variant="caption">{item.title}</Text>
              </a>
            </Box>
          ))}
        </Box>
      )}

      <PromotionFooter topic={source.column ?? null} />
    </Box>
  )
}

export default NewsSourceCard
