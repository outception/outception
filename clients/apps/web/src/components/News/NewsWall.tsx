'use client'

import { useDefaultDeck, useNewsSources } from '@/hooks/queries/news'
import { useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { WEATHER_SOURCE_ID, WEATHER_SOURCE_META } from '@/utils/weather'
import { Button, Spinner, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useSearchParams } from 'next/navigation'
import { useEffect, useMemo } from 'react'
import { useNewsColumn } from './NewsColumnContext'
import { NewsDeck } from './NewsDeck'
import { setSeedDeck } from './newsPrefsStore'
import { NewsSearchDialog } from './NewsSearchDialog'

/** The public news wall body: a swipe deck of either your followed sources
 * ("Your deck") or every source ("Trending"). A fresh visitor's empty deck is
 * seeded with the reader's country news (geo default); once the user has
 * followed or unfollowed anything, an empty deck stays empty and offers the
 * source palette instead. The tabs, "More" palette and theme-toggle logo live
 * in the top navbar (see LandingLayout). */
export const NewsWall = ({ focusTopic }: { focusTopic?: string } = {}) => {
  const { focused, hidden, everFollowed, isFailed, setSearchOpen } =
    useNewsColumn()
  const { data: sources, isLoading: sourcesLoading } = useNewsSources()
  const t = useT()
  // A shared card link (?card=<id>) opens the wall on that exact source.
  const sharedCardId = useSearchParams().get('card') ?? undefined
  // Seeding only applies to a fresh visitor (never followed anything) —
  // don't fetch the default category deck for anyone who has curated.
  const seeding = focused.length === 0 && !everFollowed
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
    // The weather card is synthetic (not in /news/sources); add it so a
    // "weather" id — in the seeded deck OR the followed set — resolves, unless
    // the reader unfollowed it, in which case it stays off the wall.
    if (!hidden.includes(WEATHER_SOURCE_ID)) {
      byId.set(WEATHER_SOURCE_ID, WEATHER_SOURCE_META)
    }
    // The followed set wins (in follow order). A fresh visitor who has never
    // followed is seeded with the curated default deck; a curator who emptied
    // their deck gets an empty wall — not a refill of sources they never asked
    // for.
    let ids: readonly string[]
    if (focused.length > 0) ids = focused
    else if (seeding) ids = defaultDeckIds ?? []
    else ids = []
    const deck = ids
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => Boolean(s))
    // Weather is a utility card, not news — keep it at the END of the wall.
    const weather = deck.filter((s) => s.id === WEATHER_SOURCE_ID)
    const news = deck.filter((s) => s.id !== WEATHER_SOURCE_ID)
    // A shared card link surfaces its source at the FRONT of the wall even if
    // the recipient doesn't follow it, so they land on exactly what was shared.
    if (sharedCardId && !deck.some((s) => s.id === sharedCardId)) {
      const shared =
        byId.get(sharedCardId) ??
        (sources ?? []).find((s) => s.id === sharedCardId)
      if (shared) return [shared, ...news, ...weather]
    }
    if (news.length === 0 && weather.length === 0) return []
    return [...news, ...weather]
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
