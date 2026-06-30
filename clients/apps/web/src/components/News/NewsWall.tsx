'use client'

import { useDefaultDeck, useNewsSources } from '@/hooks/queries/news'
import type { NewsSourceMeta } from '@/utils/news'
import { Spinner } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useMemo } from 'react'
import { useNewsColumn } from './NewsColumnContext'
import { NewsDeck } from './NewsDeck'
import { NewsSearchDialog } from './NewsSearchDialog'

/** The public news wall body: a swipe deck of either your followed sources
 * ("Your deck") or every source ("Trending"). When "Your deck" is empty it is
 * seeded with the reader's country news (geo default). The tabs, "More" palette
 * and theme-toggle logo live in the top navbar (see LandingLayout). */
export const NewsWall = () => {
  const { tab, focused, isFailed } = useNewsColumn()
  const { data: sources, isLoading } = useNewsSources()
  // Only needed to fill an empty "Your deck".
  const { data: defaultDeckIds } = useDefaultDeck(tab === 'focus')

  const all: NewsSourceMeta[] = useMemo(
    () => (sources ?? []).filter((s) => !s.redirect && !isFailed(s.id)),
    [sources, isFailed],
  )

  const visible: NewsSourceMeta[] = useMemo(() => {
    if (tab !== 'focus') return all
    const focusedSet = new Set(focused)
    const own = all.filter((s) => focusedSet.has(s.id))
    if (own.length > 0) return own
    // Empty "Your deck": seed with the reader's country news (geo default),
    // in the order the backend returns.
    const byId = new Map(all.map((s) => [s.id, s]))
    return (defaultDeckIds ?? [])
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => Boolean(s))
  }, [tab, all, focused, defaultDeckIds])

  return (
    <Box
      flexDirection="column"
      rowGap="xl"
      paddingVertical="xl"
      flexGrow={1}
      justifyContent="center"
    >
      {isLoading ? (
        <Box justifyContent="center" padding="xl">
          <Spinner />
        </Box>
      ) : visible.length === 0 ? null : (
        <NewsDeck sources={visible} column={tab} />
      )}

      <NewsSearchDialog />
    </Box>
  )
}

export default NewsWall
