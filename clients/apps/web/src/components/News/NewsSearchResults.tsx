'use client'

import { useNewsSearch } from '@/hooks/queries/news'
import { safeExternalHref } from '@/utils/news'
import { Pill, Spinner, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'

export const NewsSearchResults = ({ query }: { query: string }) => {
  const { data, isLoading } = useNewsSearch(query)

  if (isLoading) {
    return (
      <Box justifyContent="center" padding="xl">
        <Spinner />
      </Box>
    )
  }

  const sources = data?.sources ?? []
  const items = data?.items ?? []

  if (sources.length === 0 && items.length === 0) {
    return (
      <Text color="muted">
        No results for “{query}”. Headline search only covers sources the wall
        has recently shown.
      </Text>
    )
  }

  return (
    <Box flexDirection="column" rowGap="xl">
      {sources.length > 0 && (
        <Box flexDirection="column" rowGap="s">
          <Text variant="heading-xs" as="h2">
            Sources
          </Text>
          <Box flexDirection="row" flexWrap="wrap" columnGap="s" rowGap="s">
            {sources.map((s) => (
              <a
                key={s.id}
                href={safeExternalHref(s.home)}
                target="_blank"
                rel="noreferrer"
              >
                <Pill color="gray">{s.name}</Pill>
              </a>
            ))}
          </Box>
        </Box>
      )}

      {items.length > 0 && (
        <Box flexDirection="column" rowGap="s">
          <Text variant="heading-xs" as="h2">
            Headlines
          </Text>
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
        </Box>
      )}
    </Box>
  )
}
