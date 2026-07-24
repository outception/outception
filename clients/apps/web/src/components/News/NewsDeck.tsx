'use client'

import { useLocale } from '@/providers/locale'
import type { NewsSourceMeta } from '@/utils/news'
import { Box } from '@outception-com/orbit/Box'
import { AdSenseUnit } from '@/components/Ads/AdSenseUnit'
import { CONFIG } from '@/utils/config'
import { isRtlLocale } from '@outception-com/i18n'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { motion } from 'motion/react'
import { SwipeDeckCard } from './SwipeDeckCard'
import { useSwipeDeck } from './useSwipeDeck'

// One upcoming card peeks on the right, mirroring the previous card on the left.
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

const NAV_BUTTON =
  'cursor-pointer rounded-xl border border-neutral-400/30 p-1.5 transition-colors hover:bg-neutral-400/10 disabled:cursor-default disabled:opacity-40 disabled:hover:bg-transparent'

/**
 * Swipeable card deck: the centred card follows the finger in any direction and
 * rotates, then commits on a fast flick OR a short drag, springing back below
 * the threshold. Swiping left/up advances, right/down goes back — the previous
 * and upcoming cards peek out behind. The arrows mirror this, and position
 * persists per column.
 */
export const NewsDeck = ({
  sources,
  column,
  initialActiveId,
}: {
  sources: NewsSourceMeta[]
  column: string
  initialActiveId?: string
}) => {
  const items = sources.map((s) => s.id)
  const deck = useSwipeDeck(items, column, initialActiveId)
  const rtl = isRtlLocale(useLocale())
  // Under dir="rtl" the flex nav row auto-reverses (Previous ends up on the
  // right), so the chevrons must swap to keep pointing the way the deck moves.
  const PrevIcon = rtl ? ChevronRight : ChevronLeft
  const NextIcon = rtl ? ChevronLeft : ChevronRight

  if (!sources.length) return null

  const byId = new Map(sources.map((s) => [s.id, s]))
  // Mounted window: the previous card (peeking left), the current one, and the
  // next card(s) peeking right. Indices wrap so the deck loops — at the last
  // card the upcoming peek is the first card, and vice versa. Keyed by id so
  // each card keeps its node and glides between slots as the index moves. With
  // very few cards we trim the offsets to keep every id (and React key) unique.
  const len = items.length
  const offsets =
    len > 2 ? [-1, 0, WINDOW_AHEAD] : len === 2 ? [0, WINDOW_AHEAD] : [0]
  const windowed = offsets.map((depth) => ({
    id: items[(((deck.index + depth) % len) + len) % len],
    depth,
  }))

  return (
    <Box
      flexDirection="column"
      alignItems="center"
      rowGap="l"
      paddingBottom="m"
    >
      <motion.div
        key={column}
        initial={{ opacity: 0, y: 18, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 30 }}
        // Desktop: no clipping — the neighbouring sheets are fully visible,
        // poking out past the deck with their real edges and tilt, like papers
        // spread on a desk. Mobile still clips with a short fade (the page is
        // only as wide as the deck there, so overflow would cause sideways
        // scrolling).
        className="relative h-[62vh] min-h-[460px] w-full max-w-2xl overflow-x-clip [mask-image:linear-gradient(to_right,transparent_0,black_16px,black_calc(100%-16px),transparent_100%)] md:h-[62vh] md:min-h-[500px] md:overflow-x-visible md:[mask-image:none]"
      >
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
      </motion.div>

      {/* One shared AdSense unit for the whole deck (not per-card — the deck
          mounts up to 3 cards for the swipe animation, and one ad per view is
          the policy-safe pattern). Sits below the card, above the nav. */}
      {CONFIG.ADSENSE_SLOT_WALL && (
        <Box width="100%" maxWidth={672} justifyContent="center">
          <AdSenseUnit slot={CONFIG.ADSENSE_SLOT_WALL} className="w-full" />
        </Box>
      )}

      <div className="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-400">
        <button
          type="button"
          aria-label="Previous"
          disabled={!deck.canPrev}
          onClick={deck.goPrev}
          className={NAV_BUTTON}
        >
          <PrevIcon className="h-4 w-4" />
        </button>
        {/* Every deck — small or the 60-source Trending deck — reads as the
            same windowed pip strip: dots with the current card as a wider
            pill. No numeric readout. The visually-hidden live region keeps the
            position available to assistive tech without showing a number. */}
        <span className="flex items-center gap-1.5">
          <span className="sr-only" aria-live="polite">
            {deck.position} / {deck.total}
          </span>
          {pipWindow(deck.position, deck.total).map((i) => (
            <span
              key={i}
              aria-hidden
              className={
                i === deck.position
                  ? 'ink-fill h-1.5 w-5 rounded-full opacity-80 transition-all duration-300'
                  : 'ink-fill h-1.5 w-1.5 rounded-full opacity-25 transition-all duration-300'
              }
            />
          ))}
        </span>
        <button
          type="button"
          aria-label="Next"
          disabled={!deck.canNext}
          onClick={deck.goNext}
          className={NAV_BUTTON}
        >
          <NextIcon className="h-4 w-4" />
        </button>
      </div>
    </Box>
  )
}
