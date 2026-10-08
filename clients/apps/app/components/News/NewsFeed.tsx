import {
  getCardsClearedSnapshot,
  getFocusedSnapshot,
  getHiddenSnapshot,
  setSeedCards,
  subscribeFocused,
  subscribeHidden,
} from '@/utils/prefs'
import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useDefaultCards, useWallSourceMetas } from '@/hooks/outception/news'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useTheme } from '@/design-system/useTheme'
import { useT } from '@/providers/translate'
import { composeDeck } from '@outception-com/news-core'
import { getSharedViewSnapshot, subscribeSharedView } from '@/utils/shareLinks'
import { getFailedSnapshot, subscribeFailed } from '@/utils/failedSources'
import { useEffect, useMemo, useSyncExternalStore } from 'react'
import { ActivityIndicator } from 'react-native'
import { NewsCards } from './NewsCards'

export type FeedMode = 'cards' | 'sources'

/** The public news feed: your device-local card set ("Your stack" - followed or, for
 * a fresh visitor, seeded with the curated default card set). The source browser
 * ("Sources") is a GlassDialog card OVER this wall (SourceSearchSheet, mounted
 * by the home screen), like the web's search dialog - so the card set stays mounted
 * and visible behind it. Following is anonymous (no login). */
export const NewsFeed = ({
  sharedCardId,
  onBrowse,
}: {
  sharedCardId?: string
  onBrowse: () => void
}) => {
  const focused = useSyncExternalStore(
    subscribeFocused,
    getFocusedSnapshot,
    getFocusedSnapshot,
  )
  const hidden = useSyncExternalStore(
    subscribeHidden,
    getHiddenSnapshot,
    getHiddenSnapshot,
  )
  const failed = useSyncExternalStore(
    subscribeFailed,
    getFailedSnapshot,
    getFailedSnapshot,
  )
  // A FRESH visitor's empty card set seeds with the curated country default - but
  // a card set the reader explicitly emptied ("Deselect all") stays empty.
  const cardsCleared = useSyncExternalStore(
    subscribeFocused,
    getCardsClearedSnapshot,
    getCardsClearedSnapshot,
  )
  // A shared deck is viewed as sent and never written into the reader's own
  // card set.
  const shared = useSyncExternalStore(
    subscribeSharedView,
    getSharedViewSnapshot,
    getSharedViewSnapshot,
  )
  const viewingShared = shared.cards.length > 0
  const seeding = !viewingShared && focused.length === 0 && !cardsCleared
  const { data: defaultCardIds, isLoading: defaultCardsLoading } =
    useDefaultCards(seeding)

  // Register the seed so the first follow promotes it into the followed set
  // (see the prefs store) instead of collapsing the card set to one card.
  useEffect(() => {
    setSeedCards(defaultCardIds ?? [])
  }, [defaultCardIds])

  // One composer for the wall, the hand and the web: the followed set wins
  // (in follow order), a fresh visitor's empty set falls back to the seed,
  // and a shared card leads even when the recipient doesn't follow it.
  const ids = useMemo(
    () =>
      composeDeck({
        followed: viewingShared ? shared.cards : focused,
        seed: defaultCardIds ?? [],
        cleared: viewingShared ? true : cardsCleared,
        hidden: viewingShared ? [] : hidden,
        sharedCard: sharedCardId,
      }),
    [
      viewingShared,
      shared.cards,
      focused,
      defaultCardIds,
      cardsCleared,
      hidden,
      sharedCardId,
    ],
  )
  // The card set paints from metadata for just these ids, never the whole
  // roster, which only the source browser needs (it loads that when it opens).
  const { data: metas, isLoading: metasLoading } = useWallSourceMetas(ids)

  const visible = useMemo<NewsSourceMeta[]>(() => {
    const failedSet = new Set(failed)
    const byId = new Map((metas ?? []).map((s) => [s.id, s] as const))
    return ids
      .map((id) => byId.get(id))
      .filter(
        (s): s is NewsSourceMeta =>
          Boolean(s) &&
          (s!.id === sharedCardId || (!s!.redirect && !failedSet.has(s!.id))),
      )
  }, [metas, ids, failed, sharedCardId])

  // A fresh reader's cards are seeded from the default-cards query; until that
  // resolves the wall is "loading", not "empty". A failed metas fetch degrades
  // to the empty state (with its Browse CTA), never to a roster-sized refetch.
  const isLoading =
    (seeding && defaultCardsLoading) || (ids.length > 0 && metasLoading)

  return (
    // paddingTop: web puts ~36px between the gem hairlines and the card
    // (header padding + the wall's own paddingVertical="xl"); the header
    // above contributes 12, this supplies the rest.
    <Box flex={1} gap="spacing-16" paddingTop="spacing-24">
      <CardsBody
        isLoading={isLoading}
        visible={visible}
        onBrowse={onBrowse}
        sharedCardId={sharedCardId}
      />
    </Box>
  )
}

export const NavTab = ({
  label,
  active,
  onPress,
}: {
  label: string
  active: boolean
  onPress: () => void
}) => (
  <Touchable onPress={onPress}>
    {/* Web's `.tab-pill`: the active tab is the paper sheet with a hairline
        ring - NOT the edition accent, which made it a saturated blob. */}
    <Box
      paddingVertical="spacing-4"
      paddingHorizontal="spacing-12"
      borderRadius="border-radius-8"
      backgroundColor={active ? 'card' : undefined}
      borderWidth={active ? 1 : 0}
      borderColor="border"
    >
      <Text
        variant={active ? 'navTabActive' : 'bodySmall'}
        color={active ? 'text' : 'subtext'}
      >
        {label}
      </Text>
    </Box>
  </Touchable>
)

/** The wall itself: nothing but the card set, mirroring the web page. Search and
 * the topic filters live behind the "Sources" tab (SourceRoster owns both), the
 * way the web keeps them inside its search dialog. */
const CardsBody = ({
  isLoading,
  visible,
  onBrowse,
  sharedCardId,
}: {
  isLoading: boolean
  visible: NewsSourceMeta[]
  onBrowse: () => void
  sharedCardId?: string
}) => {
  const t = useT()
  const theme = useTheme()

  return (
    <>
      {isLoading ? (
        <Box flex={1} justifyContent="center" alignItems="center">
          <ActivityIndicator size="large" color={theme.colors.subtext} />
        </Box>
      ) : visible.length === 0 ? (
        <Box
          flex={1}
          justifyContent="center"
          alignItems="center"
          padding="spacing-32"
          gap="spacing-8"
        >
          <Text variant="body" color="subtext" style={{ textAlign: 'center' }}>
            {t('news.cards.emptyHint')}
          </Text>
          {/* Recovery CTA (mirrors the web empty-state "Browse sources"):
              open the source browser, which owns search and the filters. */}
          <Touchable onPress={onBrowse}>
            <Box
              paddingVertical="spacing-8"
              paddingHorizontal="spacing-16"
              borderRadius="border-radius-8"
              backgroundColor="card"
            >
              <Text variant="caption" color="text">
                {t('news.cards.browse')}
              </Text>
            </Box>
          </Touchable>
        </Box>
      ) : (
        <NewsCards
          sources={visible}
          storageKey="all"
          initialActiveId={sharedCardId}
        />
      )}
    </>
  )
}
