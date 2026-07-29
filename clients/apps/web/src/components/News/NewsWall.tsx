'use client'

import { useDefaultDeck, useNewsSources } from '@/hooks/queries/news'
import { useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { Button, Spinner, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useSearchParams } from 'next/navigation'
import { useEffect, useMemo } from 'react'
import { useNewsColumn } from './NewsColumnContext'
import { NewsDeck } from './NewsDeck'
import { setSeedDeck } from './newsPrefsStore'
import { NewsSearchDialog } from './NewsSearchDialog'

/** The public news wall body: a swipe deck of either your followed sources
 * ("Your deck") or every source ("Trending"). An empty deck is always seeded
 * with the reader's country news (geo default), so the wall is never blank.
 * The tabs, "More" palette and theme-toggle logo live in the top navbar (see
 * LandingLayout). */
export const NewsWall = ({ focusTopic }: { focusTopic?: string } = {}) => {
  const { focused, hidden, isFailed, setSearchOpen } =
    useNewsColumn()
  const { data: sources, isLoading: sourcesLoading } = useNewsSources()
  const t = useT()
  // A shared card link (?card=<id>) opens the wall on that exact source.
  const sharedCardId = useSearchParams().get('card') ?? undefined
  // An empty deck always reseeds with the curated country default — the wall
  // is never blank, including right after "Deselect all".
  const seeding = focused.length === 0
  const { data: defaultDeckIds, isLoading: defaultDeckLoading } =
    useDefaultDeck(seeding)

  // Register the seeded deck so the first follow can promote it into the
  // followed set (see toggleFocus) instead of collapsing the wall to one card.
  useEffect(() => {
    setSeedDeck(defaultDeckIds ?? [])
  }, [defaultDeckIds])

  // A fresh visitor's deck is seeded from the default-deck query; until that
  // resolves their wall is "loading", not "empty" — otherwise the empty-deck
  // hint flashes at every first-time visitor.
  const isLoading = sourcesLoading || (seeding && defaultDeckLoading)

  const all: NewsSourceMeta[] = useMemo(() => {
    const hiddenSet = new Set(hidden)
    return (sources ?? []).filter(
      (s) => !s.redirect && !isFailed(s.id) && !hiddenSet.has(s.id),
    )
  }, [sources, hidden, isFailed])

  const visible: NewsSourceMeta[] = useMemo(() => {
    const byId = new Map(all.map((s) => [s.id, s]))
    // The followed set wins (in follow order); an empty followed set falls
    // back to the seeded default deck.
    let ids: readonly string[]
    if (focused.length > 0) ids = focused
    else if (seeding) ids = defaultDeckIds ?? []
    else ids = []
    const deck = ids
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => Boolean(s))
    // A shared card link surfaces its source at the FRONT of the wall even if
    // the recipient doesn't follow it, so they land on exactly what was shared.
    if (sharedCardId && !deck.some((s) => s.id === sharedCardId)) {
      const shared =
        byId.get(sharedCardId) ??
        (sources ?? []).find((s) => s.id === sharedCardId)
      if (shared) return [shared, ...deck]
    }
    return deck
  }, [all, sources, focused, seeding, defaultDeckIds, hidden, sharedCardId])

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
      ) : visible.length === 0 ? (
        <Box
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          paddingVertical="3xl"
          rowGap="l"
        >
          <Text color="muted">{t('news.deck.emptyHint')}</Text>
          <Button variant="secondary" onClick={() => setSearchOpen(true)}>
            {t('news.deck.browse')}
          </Button>
        </Box>
      ) : (
        <NewsDeck
          // Remount when arriving from a shared card (or focus topic) so the
          // deck re-opens on that card — the position is set on mount.
          key={sharedCardId ?? focusTopic ?? 'wall'}
          sources={visible}
          column="focus"
          initialActiveId={
            sharedCardId
              ? visible.find((s) => s.id === sharedCardId)?.id
              : focusTopic
                ? visible.find((s) => s.column === focusTopic)?.id
                : undefined
          }
        />
      )}

      <NewsSearchDialog />
    </Box>
  )
}
