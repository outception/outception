'use client'

import { AndroidBetaBanner } from '@/components/Landing/AndroidBeta'

import { useDefaultDeck, useWallSourceMetas } from '@/hooks/queries/news'
import { runWhenIdle } from '@/utils/idle'
import { useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { Button, Spinner, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useSyncExternalStore } from 'react'
import { GameNoteBar } from './GameNoteBar'
import { useNewsColumn } from './NewsColumnContext'
import { NewsDeck } from './NewsDeck'
import {
  getDeckClearedServerSnapshot,
  getDeckClearedSnapshot,
  setSeedDeck,
  subscribe,
} from './newsPrefsStore'
import { NewsSearchDialog } from './NewsSearchDialog'

/** The public news wall body: a swipe deck of either your followed sources
 * ("Your deck") or every source ("Trending"). An empty deck is always seeded
 * with the reader's country news (geo default), so the wall is never blank.
 * The tabs, "More" palette and theme-toggle logo live in the top navbar (see
 * LandingLayout). */
export const NewsWall = ({ focusTopic }: { focusTopic?: string } = {}) => {
  const { focused, hidden, isFailed, setSearchOpen } = useNewsColumn()
  const t = useT()
  // A shared card link (?card=<id>) opens the wall on that exact source.
  const sharedCardId = useSearchParams().get('card') ?? undefined
  // A FRESH visitor's empty deck seeds with the curated country default - but
  // a deck the reader explicitly emptied ("Deselect all") stays empty.
  const deckCleared = useSyncExternalStore(
    subscribe,
    getDeckClearedSnapshot,
    getDeckClearedServerSnapshot,
  )
  const seeding = focused.length === 0 && !deckCleared
  const { data: defaultDeckIds, isLoading: defaultDeckLoading } =
    useDefaultDeck(seeding)

  // The wall paints from metadata for just these ids - not the full
  // multi-megabyte roster, which only the search palette needs (loaded
  // lazily when it opens).
  const deckIds = useMemo<readonly string[]>(() => {
    if (focused.length > 0) return focused
    if (seeding) return defaultDeckIds ?? []
    return []
  }, [focused, seeding, defaultDeckIds])
  const wantedIds = useMemo(
    () =>
      sharedCardId && !deckIds.includes(sharedCardId)
        ? [sharedCardId, ...deckIds]
        : [...deckIds],
    [deckIds, sharedCardId],
  )
  const { data: metas, isLoading: metasLoading } = useWallSourceMetas(wantedIds)

  // Register the seeded deck so the first follow can promote it into the
  // followed set (see toggleFocus) instead of collapsing the wall to one card.
  useEffect(() => {
    setSeedDeck(defaultDeckIds ?? [])
  }, [defaultDeckIds])

  // Warm the mini-game assets once the wall idles: the deck pre-mounts a
  // game card one swipe before it arrives, and this prefetch means even that
  // mount hits a full browser cache. Deferred to idle so three.js and the
  // game pages never compete with the first cards for bandwidth.
  useEffect(() => {
    const links: HTMLLinkElement[] = []
    const cancel = runWhenIdle(() => {
      const files = [
        '/cube/index.html',
        '/cube/styles.css',
        '/cube/three.js',
        '/cube/cube.js',
        '/crossword/index.html',
        '/sudoku/index.html',
        '/solitaire/index.html',
      ]
      for (const href of files) {
        const link = document.createElement('link')
        link.rel = 'prefetch'
        link.href = href
        document.head.appendChild(link)
        links.push(link)
      }
    }, 8000)
    return () => {
      cancel()
      for (const link of links) link.remove()
    }
  }, [])

  // A fresh visitor's deck is seeded from the default-deck query; until that
  // resolves their wall is "loading", not "empty" - otherwise the empty-deck
  // hint flashes at every first-time visitor.
  const isLoading =
    (seeding && defaultDeckLoading) || (wantedIds.length > 0 && metasLoading)

  const visible: NewsSourceMeta[] = useMemo(() => {
    const byId = new Map((metas ?? []).map((s) => [s.id, s]))
    const hiddenSet = new Set(hidden)
    // The followed set wins (in follow order); an empty followed set falls
    // back to the seeded default deck (see deckIds above).
    const deck = deckIds
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => s !== undefined)
      .filter((s) => !s.redirect && !isFailed(s.id) && !hiddenSet.has(s.id))
    // A shared card link surfaces its source at the FRONT of the wall even if
    // the recipient doesn't follow it, so they land on exactly what was shared.
    if (sharedCardId && !deck.some((s) => s.id === sharedCardId)) {
      const shared = byId.get(sharedCardId)
      if (shared) return [shared, ...deck]
    }
    return deck
  }, [metas, deckIds, hidden, isFailed, sharedCardId])

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
          <Text color="muted">{t('news.deck.emptyHint')}</Text>
          <Button variant="secondary" onClick={() => setSearchOpen(true)}>
            {t('news.deck.browse')}
          </Button>
        </Box>
      ) : (
        <>
          {/* Game text (crossword byline/clue, sudoku status) lifted out of
              the card: it sits between the gem ornament above and the card
              below. Height-reserving so the deck doesn't jump. */}
          <GameNoteBar />
          <NewsDeck
            // Remount when arriving from a shared card (or focus topic) so the
            // deck re-opens on that card - the position is set on mount.
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
        </>
      )}

      <NewsSearchDialog />
    </Box>
  )
}
