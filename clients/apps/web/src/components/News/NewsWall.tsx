'use client'

import { useNewsSources } from '@/hooks/queries/news'
import type { NewsSourceMeta } from '@/utils/news'
import { Button, Grid, Input, Spinner, Text } from '@polar-sh/orbit'
import { Box } from '@polar-sh/orbit/Box'
import { useMemo, useState } from 'react'
import { ComposePromotionDialog } from '../Promotions/ComposePromotionDialog'
import { NewsSearchResults } from './NewsSearchResults'
import { NewsSourceCard } from './NewsSourceCard'

const MAX_CARDS = 12

/** The public news wall: pick a topic column, see its sources' headlines, with
 * paid promotions woven in per topic. */
export const NewsWall = () => {
  const { data: sources, isLoading } = useNewsSources()
  const [column, setColumn] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const searching = query.trim().length >= 2

  const columns = useMemo(() => {
    const set = new Set<string>()
    for (const s of sources ?? []) {
      if (s.column) set.add(s.column)
    }
    return Array.from(set).sort()
  }, [sources])

  const visible: NewsSourceMeta[] = useMemo(() => {
    const list = (sources ?? []).filter((s) => !s.redirect)
    const filtered = column ? list.filter((s) => s.column === column) : list
    return filtered.slice(0, MAX_CARDS)
  }, [sources, column])

  return (
    <Box flexDirection="column" rowGap="xl" padding="xl">
      <Box
        flexDirection="row"
        justifyContent="between"
        alignItems="center"
        flexWrap="wrap"
        rowGap="m"
      >
        <Box flexDirection="column" rowGap="xs">
          <Text variant="heading-s" as="h1">
            The Wall
          </Text>
          <Text color="muted">Live headlines · promote what matters</Text>
        </Box>
        <ComposePromotionDialog />
      </Box>

      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search headlines and sources…"
      />

      {searching ? (
        <NewsSearchResults query={query} />
      ) : (
        <>
          <Box flexDirection="row" columnGap="s" flexWrap="wrap" rowGap="s">
            <Button
              variant={column === null ? 'default' : 'secondary'}
              size="sm"
              onClick={() => setColumn(null)}
            >
              All
            </Button>
            {columns.map((c) => (
              <Button
                key={c}
                variant={column === c ? 'default' : 'secondary'}
                size="sm"
                onClick={() => setColumn(c)}
              >
                {c}
              </Button>
            ))}
          </Box>

          {isLoading ? (
            <Box justifyContent="center" padding="xl">
              <Spinner />
            </Box>
          ) : (
            <Grid
              templateColumns={{
                base: '1fr',
                md: 'repeat(2, 1fr)',
                lg: 'repeat(3, 1fr)',
              }}
              gap="l"
            >
              {visible.map((source) => (
                <NewsSourceCard key={source.id} source={source} />
              ))}
            </Grid>
          )}
        </>
      )}
    </Box>
  )
}

export default NewsWall
