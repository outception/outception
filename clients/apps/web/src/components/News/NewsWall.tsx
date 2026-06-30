'use client'

import { useNewsSources } from '@/hooks/queries/news'
import type { NewsSourceMeta } from '@/utils/news'
import { Spinner } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useEffect, useMemo, useRef } from 'react'
import { useNewsColumn } from './NewsColumnContext'
import { NewsDeck } from './NewsDeck'
import { NewsSearchDialog } from './NewsSearchDialog'

/** The public news wall body: a swipe deck of either your followed sources
 * ("Your deck") or every source ("Trending"). The tabs, "More" palette and
 * theme-toggle logo live in the top navbar (see LandingLayout). */
export const NewsWall = () => {
  const { tab, focused, setSearchOpen, isFailed } = useNewsColumn()
  const { data: sources, isLoading } = useNewsSources()

  const all: NewsSourceMeta[] = useMemo(
    () => (sources ?? []).filter((s) => !s.redirect && !isFailed(s.id)),
    [sources, isFailed],
  )

  const visible: NewsSourceMeta[] = useMemo(() => {
    if (tab !== 'focus') return all
    const focusedSet = new Set(focused)
    return all.filter((s) => focusedSet.has(s.id))
  }, [tab, all, focused])

  // When "Your deck" is empty, open the source palette automatically (once) so
  // the user can fill it — no empty-state message.
  const autoOpened = useRef(false)
  useEffect(() => {
    if (tab === 'focus' && !isLoading && visible.length === 0) {
      if (!autoOpened.current) {
        autoOpened.current = true
        setSearchOpen(true)
      }
    } else {
      autoOpened.current = false
    }
  }, [tab, isLoading, visible.length, setSearchOpen])

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
      ) : tab === 'focus' && visible.length === 0 ? null : (
        <NewsDeck sources={visible} column={tab} />
      )}

      <NewsSearchDialog />
    </Box>
  )
}

export default NewsWall
