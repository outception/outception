'use client'

import { AndroidBetaBanner } from '@/components/Landing/AndroidBeta'
import { useDefaultCards, useWallSourceMetas } from '@/hooks/queries/news'
import { useT } from '@/providers/translate'
import { getClientCountry } from '@/utils/i18n/shared'
import {
  getWallLookServerSnapshot,
  getWallLookSnapshot,
  getWallThemeServerSnapshot,
  getWallThemeSnapshot,
  setWallLook,
  setWallTheme,
  subscribeWallTheme,
} from '@/utils/wallTheme'
import {
  DEFAULT_EDITION_ID,
  PLAIN_LOOK_ID,
  buildShareLink,
  composeDeck,
  countryCardId,
  isBriefingCardId,
  isShareLink,
  markStartersOffered,
  parseShareLink,
  restoreFromLink,
  shouldOfferStarters,
  isCountryCardId,
  rankByCoverage,
  type Card,
  type ShareLinkState,
} from '@outception-com/news-core'
import { Button } from '@outception-com/orbit/Button'
import { Spinner } from '@outception-com/orbit/Spinner'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import { useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'next/navigation'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { descriptorFor, type CardDescriptor } from './Card'
import { useNewsColumn } from './NewsColumnContext'
import { NewsCards } from './NewsCards'
import {
  browserStorage,
  getBriefingProfilesServerSnapshot,
  getBriefingProfilesSnapshot,
  getCardsClearedServerSnapshot,
  getCardsClearedSnapshot,
  setSeedCards,
  subscribe,
} from './newsPrefsStore'
import { NewsSearchDialog } from './NewsSearchDialog'

const EMPTY: readonly string[] = []

/** A country's name in English for the "why this card" line; the code when
 * the runtime has no display names. */
const countryName = (code: string): string => {
  try {
    return new Intl.DisplayNames(['en'], { type: 'region' }).of(code) ?? code
  } catch {
    return code
  }
}

/** The public news wall body: a swipe deck of the reader's cards. An empty
 * deck is seeded with the reader's country default, so the wall is never
 * blank. The pills, the "Cards" palette and the edition fan live in the top
 * bar (see LandingLayout). */
/** The composed deck with its pinned head kept (the shared card, the
 * country card, the briefings) and the rest ordered by coverage. */
const rankDeck = (
  deck: string[],
  sharedCardId: string | null | undefined,
  coverageOf: (id: string) => number,
): string[] => {
  const pinned = (id: string) =>
    id === sharedCardId || isBriefingCardId(id) || isCountryCardId(id)
  let head = 0
  while (head < deck.length && pinned(deck[head] as string)) head += 1
  return [
    ...deck.slice(0, head),
    ...rankByCoverage(deck.slice(head), coverageOf),
  ]
}

export const NewsWall = ({ focusTopic }: { focusTopic?: string } = {}) => {
  const { focused, hidden, isFailed, setSearchOpen, setDeck } = useNewsColumn()
  const t = useT()
  // A shared card link (?card=<id>) opens the wall on that exact card. The
  // hash may carry the sender's whole deck, theme and story (share link v1):
  // restored once on arrival, theme first, then the cards, then the story.
  const sharedCardId = useSearchParams().get('card') ?? undefined
  const [shared, setShared] = useState<ShareLinkState | null>(null)
  const restoring = useRef(false)
  useEffect(() => {
    const state = parseShareLink({
      search: window.location.search,
      hash: window.location.hash,
    })
    if (!isShareLink(state)) return
    restoring.current = true
    restoreFromLink(state, {
      theme: (s) => {
        if (s.edition) setWallTheme(s.edition)
        if (s.look) setWallLook(s.look)
        return true
      },
      cards: (s) => {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot restore of the inbound link
        setShared(s)
        return s.cards.length > 0 || s.lead !== null
      },
      story: () => true,
    })
    restoring.current = false
  }, [])
  // A shared deck is viewed as sent and never written into the recipient's
  // own card set.
  const sharedDeck = shared?.cards ?? EMPTY
  const viewingShared = sharedDeck.length > 0

  // A FRESH visitor's empty card set seeds with the curated country default,
  // but a card set the reader explicitly emptied ("Deselect all") stays empty.
  const cardsCleared = useSyncExternalStore(
    subscribe,
    getCardsClearedSnapshot,
    getCardsClearedServerSnapshot,
  )
  const profiles = useSyncExternalStore(
    subscribe,
    getBriefingProfilesSnapshot,
    getBriefingProfilesServerSnapshot,
  )
  const seeding = !viewingShared && focused.length === 0 && !cardsCleared
  const { data: defaultCardIds, isLoading: defaultCardsLoading } =
    useDefaultCards(seeding)

  // First visit ever: open the source palette (it lands on the Starters
  // gallery) so a new reader picks a curated card set in one tap instead of
  // discovering Sources later. Once only, and never over a deep link, where
  // the reader came for a specific card.
  useEffect(() => {
    const offer = shouldOfferStarters({
      storage: browserStorage,
      deepLink: Boolean(sharedCardId || focusTopic || window.location.hash),
    })
    if (!offer) return
    markStartersOffered(browserStorage)
    setSearchOpen(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const country = getClientCountry()
  // One composer for the wall, the hand and the app: the followed set wins
  // (in follow order), a fresh visitor's empty set falls back to the seed, a
  // shared card leads, and the briefing cards follow it.
  const queryClient = useQueryClient()
  // Coverage as the wall knew it on arrival: the best outlet count among a
  // card's cached rows. Read once, so cards never jump while the reader
  // swipes; the next visit sees the new order.
  const coverageAtMount = useRef<Map<string, number> | null>(null)
  const coverageOf = useCallback(
    (id: string): number => {
      if (coverageAtMount.current === null) coverageAtMount.current = new Map()
      const known = coverageAtMount.current.get(id)
      if (known !== undefined) return known
      const cached = queryClient.getQueryData<Card>(['news', 'card', id, null])
      const rows =
        cached?.kind === 'feed'
          ? ((
              cached.payload as { items?: { publisherCount?: number | null }[] }
            ).items ?? [])
          : []
      const best = rows.reduce(
        (max, row) => Math.max(max, row.publisherCount ?? 0),
        0,
      )
      coverageAtMount.current.set(id, best)
      return best
    },
    [queryClient],
  )
  const ids = useMemo(
    () =>
      rankDeck(
        composeDeck({
          followed: viewingShared ? sharedDeck : focused,
          seed: defaultCardIds ?? [],
          cleared: viewingShared ? true : cardsCleared,
          hidden: viewingShared ? EMPTY : hidden,
          sharedCard: sharedCardId,
          countryCard: country ? countryCardId(country) : null,
          briefingProfiles: viewingShared ? EMPTY : profiles,
        }),
        sharedCardId,
        coverageOf,
      ),
    [
      coverageOf,
      viewingShared,
      sharedDeck,
      focused,
      defaultCardIds,
      cardsCleared,
      hidden,
      sharedCardId,
      country,
      profiles,
    ],
  )
  // The wall paints from metadata for just these ids, not the full roster,
  // which only the search palette needs (loaded lazily when it opens).
  const wantedIds = useMemo(
    () => ids.filter((id) => !isBriefingCardId(id)),
    [ids],
  )
  const { data: metas, isLoading: metasLoading } = useWallSourceMetas(wantedIds)

  // Register the seeded card set so the first follow can promote it into the
  // followed set (see toggleFocus) instead of collapsing the wall to one card.
  useEffect(() => {
    setSeedCards(defaultCardIds ?? [])
  }, [defaultCardIds])

  // A fresh visitor's cards are seeded from the default-cards query; until
  // that resolves their wall is "loading", not "empty".
  const isLoading =
    (seeding && defaultCardsLoading) || (wantedIds.length > 0 && metasLoading)

  const visible: CardDescriptor[] = useMemo(() => {
    const byId = new Map((metas ?? []).map((s) => [s.id, s]))
    return ids
      .map((id) => descriptorFor(id, byId.get(id)))
      .filter(
        (card): card is CardDescriptor =>
          card !== null &&
          (card.id === sharedCardId ||
            (!card.meta?.redirect && !isFailed(card.id))),
      )
  }, [metas, ids, isFailed, sharedCardId])

  // The deck on show, for the share link.
  useEffect(() => {
    setDeck(visible.map((card) => card.id))
  }, [visible, setDeck])

  const whyFor = useCallback(
    (id: string): string | null => {
      if (id === sharedCardId || viewingShared) return t('news.why.shared')
      if (!seeding) return null
      if (country && id === countryCardId(country))
        return t('news.why.country', { country: countryName(country) })
      return t('news.why.starter')
    },
    [sharedCardId, viewingShared, seeding, country, t],
  )

  // The live address carries the theme so a copied address bar still opens
  // the same look: written debounced through replaceState so the back
  // button is never polluted, and never over an inbound share hash.
  const edition = useSyncExternalStore(
    subscribeWallTheme,
    getWallThemeSnapshot,
    getWallThemeServerSnapshot,
  )
  const look = useSyncExternalStore(
    subscribeWallTheme,
    getWallLookSnapshot,
    getWallLookServerSnapshot,
  )
  useEffect(() => {
    if (restoring.current) return
    const timer = setTimeout(() => {
      const current = parseShareLink({ hash: window.location.hash })
      if (current.cards.length > 0 || current.story !== null) return
      const plain =
        edition.id === DEFAULT_EDITION_ID && look.id === PLAIN_LOOK_ID
      const built = plain
        ? ''
        : buildShareLink({
            edition: edition.id,
            look: look.id === PLAIN_LOOK_ID ? null : look.id,
          }).split('#')[1]
      const next = built ? `#${built}` : ''
      if (window.location.hash === next) return
      if (!next && !window.location.hash.startsWith('#v=')) return
      window.history.replaceState(
        window.history.state,
        '',
        `${window.location.pathname}${window.location.search}${next}`,
      )
    }, 300)
    return () => clearTimeout(timer)
  }, [edition, look])

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
          // deck re-opens on that card: the position is set on mount.
          key={sharedCardId ?? focusTopic ?? 'wall'}
          cards={visible}
          column="focus"
          initialActiveId={
            sharedCardId
              ? visible.find((c) => c.id === sharedCardId)?.id
              : focusTopic
                ? visible.find((c) => c.meta?.column === focusTopic)?.id
                : undefined
          }
          whyFor={whyFor}
          storyId={shared?.story ?? null}
        />
      )}

      <NewsSearchDialog />
    </Box>
  )
}
