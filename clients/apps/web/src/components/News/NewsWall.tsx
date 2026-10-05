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
  browserStorage,
  getCardsClearedServerSnapshot,
  getCardsClearedSnapshot,
  setSeedCards,
  subscribe,
} from './newsPrefsStore'
import {
  composeDeck,
  markStartersOffered,
  shouldOfferStarters,
} from '@outception-com/news-core'
import { NewsSearchDialog } from './NewsSearchDialog'

/** The public news wall body: a swipe card set of either your followed sources
 * ("Your stack") or every source ("Trending"). An empty card set is always seeded
 * with the reader's country news (geo default), so the wall is never blank.
 * The tabs, "Cards" palette and theme-toggle logo live in the top navbar (see
 * LandingLayout). */
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
  // discovering Sources later. Once only, and never over a shared card or
  // topic deep link, where the reader came for a specific card.
  useEffect(() => {
    const offer = shouldOfferStarters({
      storage: browserStorage,
      deepLink: Boolean(sharedCardId || focusTopic),
    })
    if (!offer) return
    markStartersOffered(browserStorage)
    setSearchOpen(true)
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
    // One composer for the wall, the hand and the app: the followed set wins
    // (in follow order), a fresh visitor's empty set falls back to the seed,
    // and a shared card leads even when the recipient doesn't follow it.
    const ids = composeDeck({
      followed: focused,
      seed: defaultCardIds ?? [],
      cleared: cardsCleared,
      hidden,
      dropped: (id) => {
        const meta = byId.get(id)
        return !meta || Boolean(meta.redirect) || isFailed(id)
      },
      sharedCard: sharedCardId,
    })
    return ids
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => s !== undefined)
  }, [
    metas,
    focused,
    defaultCardIds,
    cardsCleared,
    hidden,
    isFailed,
    sharedCardId,
  ])

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
