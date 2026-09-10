'use client'

import { AndroidBetaBanner } from '@/components/Landing/AndroidBeta'
import { EU_COUNTRY_CODES } from '@/components/Privacy/countries'
import { COOKIE_CONSENT_EVENT } from '@/components/Privacy/CookieConsent'

import { useDefaultCards, useWallSourceMetas } from '@/hooks/queries/news'
import { usePromotedSlot } from '@/hooks/queries/promoted'
import { PROMOTED_CARD_ID } from '@/utils/promoted'
import { runWhenIdle } from '@/utils/idle'
import { useT } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { Button } from '@outception-com/orbit/Button'
import { Spinner } from '@outception-com/orbit/Spinner'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import { useSearchParams } from 'next/navigation'
import { useEffect, useMemo, useSyncExternalStore } from 'react'
import { GameNoteBar } from './GameNoteBar'
import { WallZoom } from './WallZoom'
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
  const { focused, hidden, isFailed, setSearchOpen, view } = useNewsColumn()
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
      // An EU reader with the cookie banner still unanswered must answer it
      // first: the Sources dialog paints above the banner and its pointer
      // lock makes consent unclickable. Hold the welcome until the banner is
      // answered (accept OR decline both dismiss it), still on this visit;
      // if the reader leaves without answering, the un-burnt flag re-arms
      // the welcome for their next visit.
      const country = document.cookie.match(/(?:^|; )oc-geo-country=([A-Z]+)/)
      if (
        country &&
        EU_COUNTRY_CODES.includes(country[1]) &&
        localStorage.getItem('cookie_consent') === null
      ) {
        window.addEventListener(COOKIE_CONSENT_EVENT, openWelcome, {
          once: true,
        })
        return () =>
          window.removeEventListener(COOKIE_CONSENT_EVENT, openWelcome)
      }
      openWelcome()
    } catch {
      // Storage blocked (private mode): skip the tour rather than loop it.
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // The wall paints from metadata for just these ids - not the full
  // multi-megabyte roster, which only the search palette needs (loaded
  // lazily when it opens).
  // Cards or mosaic. Deliberately NOT persisted: the mosaic is a way to look
  // over everything at once, not a home you settle into, so a return visit
  // opens on the cards the way it always has.

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

  // Warm the mini-game assets once the wall idles: the card set pre-mounts a
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

  // A fresh visitor's cards are seeded from the default-cards query; until that
  // resolves their wall is "loading", not "empty" - otherwise the empty-cards
  // hint flashes at every first-time visitor.
  const isLoading =
    (seeding && defaultCardsLoading) || (wantedIds.length > 0 && metasLoading)

  // At most ONE Promoted card per card set serve: while a run is active, a
  // synthetic card set entry goes in at position 2 - seen on the first swipe,
  // never the landing card. The card itself reads the slot from the same
  // cached query (see PromotedCard).
  const { data: promotedSlot } = usePromotedSlot()

  const visible: NewsSourceMeta[] = useMemo(() => {
    const byId = new Map((metas ?? []).map((s) => [s.id, s]))
    const hiddenSet = new Set(hidden)
    // The followed set wins (in follow order); an empty followed set falls
    // back to the seeded default card set (see cardIds above).
    const cards = cardIds
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => s !== undefined)
      .filter((s) => !s.redirect && !isFailed(s.id) && !hiddenSet.has(s.id))
    if (promotedSlot && cards.length > 0) {
      cards.splice(Math.min(1, cards.length), 0, {
        id: PROMOTED_CARD_ID,
        name: promotedSlot.businessName,
        color: '#e81c2e',
        interval: 0,
      })
    }
    // A shared card link surfaces its source at the FRONT of the wall even if
    // the recipient doesn't follow it, so they land on exactly what was shared.
    if (sharedCardId && !cards.some((s) => s.id === sharedCardId)) {
      const shared = byId.get(sharedCardId)
      if (shared) return [shared, ...cards]
    }
    return cards
  }, [metas, cardIds, hidden, isFailed, sharedCardId, promotedSlot])

  return (
    <Box
      flexDirection="column"
      rowGap={view === 'zoom' ? 'none' : { base: 's', md: 'xl' }}
      // The mosaic fills the screen from the very top and runs under the
      // navbar, which is sticky and floats over it. The card view keeps its
      // breathing room: a single centred card needs the space, a wall of
      // ninety tiles is spoiled by it.
      paddingVertical={view === 'zoom' ? 'none' : { base: 'm', md: 'xl' }}
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
        <>
          {/* Game text (crossword byline/clue, sudoku status) lifted out of
              the card: it sits between the gem ornament above and the card
              below. Height-reserving so the card set doesn't jump. */}
          {/* The gem ornament and game strip belong to the card view. The
              strip is sticky, so in the mosaic it pinned itself over the tiles
              with nothing behind it - the overlap seen when scrolling back up.
              The logo's fan carries the mosaic control instead. */}
          {view === 'cards' && <GameNoteBar />}
          {view === 'zoom' ? (
            <div className="wall-view-swap w-full">
              <WallZoom ids={visible.map((s) => s.id)} metas={metas} />
            </div>
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
        </>
      )}

      <NewsSearchDialog />
    </Box>
  )
}
