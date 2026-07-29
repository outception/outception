import { Box } from '@/components/Shared/Box'
import { AutoSpinningLogo } from '@/components/Shared/SpinningLogo'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useDefaultDeck, useNewsSources } from '@/hooks/outception/news'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useT } from '@/providers/LocaleProvider'
import { hasGameWebView } from '@/utils/news'
import {
  getDeckClearedSnapshot,
  getFocusedSnapshot,
  setSeedDeck,
  subscribeFocused,
} from '@/utils/focusedSources'
import { getFailedSnapshot, subscribeFailed } from '@/utils/failedSources'
import { getHiddenSnapshot, subscribeHidden } from '@/utils/hiddenSources'
import { useEffect, useMemo, useSyncExternalStore } from 'react'
import { NewsDeck } from './NewsDeck'

export type FeedMode = 'deck' | 'sources'

/** The public news feed: your device-local deck ("Your deck" — followed or, for
 * a fresh visitor, seeded with the curated default deck). The source browser
 * ("Sources") is a GlassDialog card OVER this wall (SourceSearchSheet, mounted
 * by the home screen), like the web's search dialog — so the deck stays mounted
 * and visible behind it. Following is anonymous (no login). */
export const NewsFeed = ({
  sharedCardId,
  onBrowse,
}: {
  sharedCardId?: string
  onBrowse: () => void
}) => {
  const { data: sources, isLoading: sourcesLoading } = useNewsSources()
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
  // A FRESH visitor's empty deck seeds with the curated country default — but
  // a deck the reader explicitly emptied ("Deselect all") stays empty.
  const deckCleared = useSyncExternalStore(
    subscribeFocused,
    getDeckClearedSnapshot,
    getDeckClearedSnapshot,
  )
  const seeding = focused.length === 0 && !deckCleared
  const { data: defaultDeckIds, isLoading: defaultDeckLoading } =
    useDefaultDeck(seeding)

  // Register the seed so the first follow promotes it into the followed set
  // (see focusedSources.toggleFocus) instead of collapsing the deck to one card.
  useEffect(() => {
    setSeedDeck(defaultDeckIds ?? [])
  }, [defaultDeckIds])

  const visible = useMemo<NewsSourceMeta[]>(() => {
    const hiddenSet = new Set(hidden)
    const failedSet = new Set(failed)
    const games = hasGameWebView()
    const list = (sources ?? []).filter(
      // Game cards render in a WebView — only on runtimes that carry the
      // native module (builds 22+); older runtimes keep filtering them.
      (s) =>
        !s.redirect &&
        (games || s.type !== 'game') &&
        !hiddenSet.has(s.id) &&
        !failedSet.has(s.id),
    )
    const byId = new Map(list.map((s) => [s.id, s]))
    // Your deck: the followed set wins; an empty followed set falls back to
    // the seeded default deck.
    let ids: readonly string[]
    if (focused.length > 0) ids = focused
    else if (seeding) ids = defaultDeckIds ?? []
    else ids = []
    const deck = ids
      .map((id) => byId.get(id))
      .filter((s): s is NewsSourceMeta => Boolean(s))
    // A shared card link surfaces its source at the FRONT of the wall even if
    // the recipient doesn't follow it, so they land on exactly what was shared.
    // Mirrors the web wall.
    if (sharedCardId && !deck.some((s) => s.id === sharedCardId)) {
      const shared =
        byId.get(sharedCardId) ??
        (sources ?? []).find((s) => s.id === sharedCardId)
      if (shared) return [shared, ...deck]
    }
    return deck
  }, [sources, hidden, failed, focused, seeding, defaultDeckIds, sharedCardId])

  const isLoading = sourcesLoading || (seeding && defaultDeckLoading)

  return (
    // paddingTop: web puts ~36px between the gem hairlines and the card
    // (header padding + the wall's own paddingVertical="xl"); the header
    // above contributes 12, this supplies the rest.
    <Box flex={1} gap="spacing-16" paddingTop="spacing-24">
      <DeckBody
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
        ring — NOT the edition accent, which made it a saturated blob. */}
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

/** The wall itself: nothing but the deck, mirroring the web page. Search and
 * the topic filters live behind the "Sources" tab (SourceRoster owns both), the
 * way the web keeps them inside its search dialog. */
const DeckBody = ({
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

  return (
    <>
      {isLoading ? (
        <Box flex={1} justifyContent="center" alignItems="center">
          {/* The native splash shows this same mark as a static image; looping
              the spin here makes it appear to come alive while the wall loads. */}
          <AutoSpinningLogo size={96} />
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
            {t('news.deck.emptyHint')}
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
                {t('news.deck.browse')}
              </Text>
            </Box>
          </Touchable>
        </Box>
      ) : (
        <NewsDeck
          sources={visible}
          storageKey="all"
          initialActiveId={sharedCardId}
        />
      )}
    </>
  )
}
