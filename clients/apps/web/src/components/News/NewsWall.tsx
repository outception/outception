'use client'

import { AndroidBetaBanner } from '@/components/Landing/AndroidBeta'

import { useDefaultCards, useWallSourceMetas } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import type { NewsSourceMeta } from '@/utils/news'
import { Button } from '@outception-com/orbit/Button'
import { Spinner } from '@outception-com/orbit/Spinner'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import { useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useSyncExternalStore } from 'react'
import { useNewsColumn } from './NewsColumnContext'
import { NewsCards } from './NewsCards'
import {
  getCardsClearedServerSnapshot,
  getCardsClearedSnapshot,
  setSeedCards,
  subscribe,
} from './newsPrefsStore'
import { NewsSearchDialog } from './NewsSearchDialog'

/** The public news wall body: a swipe card set of either your followed sources
 * ("Your stack") or every source ("Trending"). An empty card set is always seeded
 * with the reader's country news (geo default), so the wall is never blank.
 * The tabs, "Cards" palette and theme-toggle logo live in the top navbar (see
 * LandingLayout). */
// Guards the one-time Starters welcome; versioned so a future onboarding
// revamp can re-show it deliberately.
const FIRST_VISIT_KEY = 'news:first-visit:v1'

export const NewsWall = ({ focusTopic }: { focusTopic?: string } = {}) => {
  const { focused, hidden, isFailed, setSearchOpen } = useNewsColumn()
  const t = useT()
  // A shared card link (?card=<id>) opens the wall on that exact source.
  const sharedCardId = useSearchParams().get('card') ?? undefined
  // A FRESH visitor's empty card set seeds with the curated country default - but
  // a card set the reader explicitly emptied ("Deselect all") stays empty.
  const cardsCleared = useSyncExternalStore(
    subscribe,
    getCardsClearedSnapshot,
    getCardsClearedServerSnapshot,
  )
  const seeding = focused.length === 0 && !cardsCleared
  const { data: defaultCardIds, isLoading: defaultCardsLoading } =
    useDefaultCards(seeding)

  // First visit ever: open the source palette (it lands on the Starters
  // gallery) so a new reader picks a curated card set in one tap instead of
  // discovering Sources later. Once only - the flag is set immediately, so
  // closing it never nags again - and never over a shared-card or topic
  // deep link, where the reader came for a specific card.
  useEffect(() => {
    if (sharedCardId || focusTopic) return
    const openWelcome = () => {
      try {
        localStorage.setItem(FIRST_VISIT_KEY, '1')
        if (localStorage.getItem('news.focusedSources') === null) {
          setSearchOpen(true)
        }
      } catch {
        // Storage blocked (private mode): skip the tour rather than loop it.
      }
    }
    try {
      if (localStorage.getItem(FIRST_VISIT_KEY)) return
      openWelcome()
    } catch {
      // Storage blocked (private mode): skip the tour rather than loop it.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // The wall paints from metadata for just these ids - not the full
  // multi-megabyte roster, which only the search palette needs (loaded
  // lazily when it opens).
  const cardIds = useMemo<readonly string[]>(() => {
    if (focused.length > 0) return focused
    if (seeding) return defaultCardIds ?? []
    return []
  }, [focused, seeding, defaultCardIds])
  const wantedIds = useMemo(
    () =>
      sharedCardId && !cardIds.includes(sharedCardId)
        ? [sharedCardId, ...cardIds]
        : [...cardIds],
    [cardIds, sharedCardId],
  )
  const { data: metas, isLoading: metasLoading } = useWallSourceMetas(wantedIds)

  // Register the seeded card set so the first follow can promote it into the
  // followed set (see toggleFocus) instead of collapsing the wall to one card.
  useEffect(() => {
    setSeedCards(defaultCardIds ?? [])
  }, [defaultCardIds])

  // A fresh visitor's cards are seeded from the default-cards query; until that
  // resolves their wall is "loading", not "empty" - otherwise the empty-cards
  // hint flashes at every first-time visitor.
  const isLoading =
    (seeding && defaultCardsLoading) || (wantedIds.length > 0 && metasLoading)

  const visible: NewsSourceMeta[] = useMemo(() => {
    const byId = new Map((metas ?? []).map((s) => [s.id, s]))
    const hiddenSet = new Set(hidden)
    // The followed set wins (in follow order); an empty followed set falls
    // back to the seeded default card set (see cardIds above).
    const cards = cardIds
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => s !== undefined)
      .filter((s) => !s.redirect && !isFailed(s.id) && !hiddenSet.has(s.id))
    // A shared card link surfaces its source at the FRONT of the wall even if
    // the recipient doesn't follow it, so they land on exactly what was shared.
    if (sharedCardId && !cards.some((s) => s.id === sharedCardId)) {
      const shared = byId.get(sharedCardId)
      if (shared) return [shared, ...cards]
    }
    return cards
  }, [metas, cardIds, hidden, isFailed, sharedCardId])

  return (
    <Box
      flexDirection="column"
      rowGap={{ base: 's', md: 'xl' }}
      paddingVertical={{ base: 'm', md: 'xl' }}
      flexGrow={1}
      justifyContent={{ base: 'start', md: 'center' }}
    >
      {/* Android visitors only: recruits the exact audience that wants the
          app into the closed beta (renders null everywhere else). */}
      <AndroidBetaBanner />
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
          <Text color="muted">{t('news.cards.emptyHint')}</Text>
          <Button variant="secondary" onClick={() => setSearchOpen(true)}>
            {t('news.cards.browse')}
          </Button>
        </Box>
      ) : (
        <NewsCards
          // Remount when arriving from a shared card (or focus topic) so the
          // card set re-opens on that card - the position is set on mount.
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
