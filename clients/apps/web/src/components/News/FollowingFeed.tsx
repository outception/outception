'use client'

import { useFollowedFeed } from '@/hooks/queries/news'
import { safeExternalHref } from '@/utils/news'
import { Spinner, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'

export const FollowingFeed = () => {
  const { data, isLoading } = useFollowedFeed()

  if (isLoading) {
    return (
      <Box justifyContent="center" padding="xl">
        <Spinner />
      </Box>
    )
  }

  const items = data?.items ?? []

  if (items.length === 0) {
    return (
      <Text color="muted">
        Follow some sources with the ☆ button to build your feed. New headlines
        appear here as the wall warms them.
      </Text>
    )
  }

  return (
    <Box flexDirection="column" rowGap="s">
      {items.map((hit, i) => (
        <a
          key={`${hit.sourceId}-${i}`}
          href={safeExternalHref(hit.item.url)}
          target="_blank"
          rel="noreferrer"
        >
          <Box
            flexDirection="column"
            rowGap="xs"
            padding="m"
            borderRadius="m"
            backgroundColor="background-card"
          >
            <Text variant="body">{hit.item.title}</Text>
            <Text variant="caption" color="muted">
              {hit.sourceName}
            </Text>
          </Box>
        </a>
      ))}
    </Box>
  )
}
