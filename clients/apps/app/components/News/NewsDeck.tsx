import { Box } from '@/components/Shared/Box'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useLocale } from '@/providers/LocaleProvider'
import MaterialIcons from '@expo/vector-icons/MaterialIcons'
import { isRtlLocale } from '@outception-com/i18n'
import { AdBanner } from '@/components/Ads/AdBanner'
import { SwipeDeckCard } from './SwipeDeckCard'
import { useSwipeDeck } from './useSwipeDeck'

// One upcoming card peeks ahead, mirroring the previous card behind.
const WINDOW_AHEAD = 1

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

/**
 * Swipeable card deck: the centred card follows the finger and rotates, then
 * commits on a fast flick OR a short drag, springing back below the threshold.
 * Swiping left/up advances, right/down goes back (mirrored in RTL). The arrows
 * mirror this. Ports the web NewsDeck to React Native.
 */
export const NewsDeck = ({
  sources,
  storageKey,
}: {
  sources: NewsSourceMeta[]
  storageKey?: string
}) => {
  const theme = useTheme()
  const items = sources.map((s) => s.id)
  const deck = useSwipeDeck(items, storageKey)
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
    <Box flex={1} gap="spacing-16" paddingHorizontal="spacing-16">
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
              onSwipe={(move) =>
                move === 'next' ? deck.goNext() : deck.goPrev()
              }
            />
          )
        })}
      </Box>

      {/* One anchored banner for the whole deck (not per-card — the deck mounts
          up to 3 cards for the swipe animation, and AdMob wants a single banner
          per screen). Sits at the bottom of the card area, above the nav. */}
      <Box alignItems="center">
        <AdBanner />
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
          accessibilityLabel="Previous"
        >
          <Box
            padding="spacing-6"
            borderRadius="border-radius-12"
            borderWidth={1}
            borderColor="border"
            style={{ opacity: deck.canPrev ? 1 : 0.4 }}
          >
            <MaterialIcons
              name={prevIcon}
              size={20}
              color={theme.colors.subtext}
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
            <Box
              key={i}
              height={6}
              width={i === deck.position ? 20 : 6}
              borderRadius="border-radius-999"
              backgroundColor="text"
              style={{ opacity: i === deck.position ? 0.8 : 0.25 }}
            />
          ))}
        </Box>

        <Touchable
          onPress={deck.goNext}
          disabled={!deck.canNext}
          accessibilityLabel="Next"
        >
          <Box
            padding="spacing-6"
            borderRadius="border-radius-12"
            borderWidth={1}
            borderColor="border"
            style={{ opacity: deck.canNext ? 1 : 0.4 }}
          >
            <MaterialIcons
              name={nextIcon}
              size={20}
              color={theme.colors.subtext}
            />
          </Box>
        </Touchable>
      </Box>
    </Box>
  )
}
