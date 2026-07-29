import { Box } from '@/components/Shared/Box'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useLocale, useT } from '@/providers/LocaleProvider'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import { isRtlLocale } from '@outception-com/i18n'
import { SwipeDeckCard } from './SwipeDeckCard'
import { useSwipeDeck } from './useSwipeDeck'
import { useCallback, useMemo, useRef, useSyncExternalStore } from 'react'
import Animated, { useAnimatedStyle, withTiming } from 'react-native-reanimated'
import {
  getFocusRequestSnapshot,
  subscribeFocused,
} from '@/utils/focusedSources'

// One upcoming card peeks ahead, mirroring the previous card behind.
const WINDOW_AHEAD = 1

// Height reserved under the cards for the compact ad banner (50dp unit plus a
// hair of air) - the cards' bottom inset, so the banner reads as the deck's
// foot rather than a separate bar.

// Max pips shown at once. Small decks show every card; larger decks (e.g. the
// 60-source Trending deck) show a sliding window centred on the current card,
// so the readout stays a clean line strip instead of a number.
const MAX_PIPS = 7

// 1-based indices of the pips to render around the current position.
const pipWindow = (position: number, total: number): number[] => {
  const count = Math.min(MAX_PIPS, total)
  const half = Math.floor(count / 2)
  const end = Math.min(total, Math.max(1, position - half) + count - 1)
  const start = Math.max(1, end - count + 1)
  return Array.from({ length: end - start + 1 }, (_, i) => start + i)
}

/** One pagination pip: the active pip stretches (6→20) and brightens with the
 * web's 300ms ease instead of snapping between states. */
const Pip = ({ active, color }: { active: boolean; color: string }) => {
  const theme = useTheme()
  const style = useAnimatedStyle(
    () => ({
      width: withTiming(active ? 20 : 6, { duration: 300 }),
      opacity: withTiming(active ? 0.8 : 0.25, { duration: 300 }),
    }),
    [active],
  )
  return (
    <Animated.View
      style={[
        {
          height: theme.dimension['dimension-6'],
          borderRadius: theme.borderRadii['border-radius-999'],
          backgroundColor: color,
        },
        style,
      ]}
    />
  )
}

/**
 * Swipeable card deck: the centred card follows the finger and rotates, then
 * commits on a fast flick OR a short drag, springing back below the threshold.
 * Swiping left/up advances, right/down goes back (mirrored in RTL). The arrows
 * mirror this. Ports the web NewsDeck to React Native.
 */
export const NewsDeck = ({
  sources,
  storageKey,
  initialActiveId,
}: {
  sources: NewsSourceMeta[]
  storageKey?: string
  initialActiveId?: string
}) => {
  const theme = useTheme()
  const focusRequest = useSyncExternalStore(
    subscribeFocused,
    getFocusRequestSnapshot,
    getFocusRequestSnapshot,
  )
  const t = useT()
  // Memoised: a fresh array each render re-creates `move` and re-fires
  // useSwipeDeck's effects on every repaint.
  const items = useMemo(() => sources.map((s) => s.id), [sources])
  const deck = useSwipeDeck(items, storageKey, focusRequest, initialActiveId)
  // Ref-backed so the callback identity NEVER changes: an inline closure here
  // would defeat SwipeDeckCard's memo on every deck re-render.
  const deckRef = useRef(deck)
  deckRef.current = deck
  const handleSwipe = useCallback((move: 'next' | 'prev') => {
    if (move === 'next') deckRef.current.goNext()
    else deckRef.current.goPrev()
  }, [])
  const rtl = isRtlLocale(useLocale())
  // The nav row auto-reverses under RTL, so swap the chevrons to keep them
  // pointing the way the deck moves.
  const prevIcon = rtl ? 'chevron-right' : 'chevron-left'
  const nextIcon = rtl ? 'chevron-left' : 'chevron-right'

  if (!sources.length) return null

  const byId = new Map(sources.map((s) => [s.id, s]))
  const len = items.length
  const offsets =
    len > 2 ? [-1, 0, WINDOW_AHEAD] : len === 2 ? [0, WINDOW_AHEAD] : [0]
  const windowed = offsets.map((depth) => ({
    id: items[(((deck.index + depth) % len) + len) % len],
    depth,
  }))

  return (
    <Box flex={1} gap="spacing-16" paddingHorizontal="spacing-4">
      {/* No minHeight: the card takes whatever the column leaves after the ad
          slot, nav row and footer, so it can never push them off-screen. The
          overflow this once guarded against is handled at the source now - the
          ad slot reserves a fixed height and the card clips partial rows.

          */}
      <Box flex={1} style={{ position: 'relative' }}>
        {/* No MaskedView here: wrapping the deck in a mask layer put a view
            between the finger and the pan gesture, which stopped swiping on
            iOS. The web's 16px edge fade is cosmetic, so the peeking cards
            simply clip at the screen edge instead. */}
        <Box flex={1} style={{ position: 'relative' }}>
          {windowed.map(({ id, depth }) => {
            const source = byId.get(id)
            if (!source) return null
            return (
              <SwipeDeckCard
                key={id}
                source={source}
                depth={depth}
                canNext={deck.canNext}
                canPrev={deck.canPrev}
                rtl={rtl}
                onSwipe={handleSwipe}
              />
            )
          })}
        </Box>
      </Box>

      <Box
        flexDirection={rtl ? 'row-reverse' : 'row'}
        alignItems="center"
        justifyContent="center"
        gap="spacing-16"
        paddingBottom="spacing-8"
      >
        <Touchable
          onPress={deck.goPrev}
          disabled={!deck.canPrev}
          accessibilityLabel={t('news.deck.previous')}
        >
          <Box
            padding="spacing-6"
            borderRadius="border-radius-12"
            borderWidth={1}
            borderColor="pageEndBorder"
            style={{ opacity: deck.canPrev ? 1 : 0.4 }}
          >
            <MaterialIcons
              name={prevIcon}
              size={16}
              color={theme.colors.pageEndText}
            />
          </Box>
        </Touchable>

        <Box
          flexDirection="row"
          alignItems="center"
          gap="spacing-6"
          accessibilityLabel={`${deck.position} / ${deck.total}`}
        >
          {pipWindow(deck.position, deck.total).map((i) => (
            <Pip
              key={i}
              active={i === deck.position}
              color={theme.colors.pageEndText}
            />
          ))}
        </Box>

        <Touchable
          onPress={deck.goNext}
          disabled={!deck.canNext}
          accessibilityLabel={t('news.deck.next')}
        >
          <Box
            padding="spacing-6"
            borderRadius="border-radius-12"
            borderWidth={1}
            borderColor="pageEndBorder"
            style={{ opacity: deck.canNext ? 1 : 0.4 }}
          >
            <MaterialIcons
              name={nextIcon}
              size={16}
              color={theme.colors.pageEndText}
            />
          </Box>
        </Touchable>
      </Box>
    </Box>
  )
}
