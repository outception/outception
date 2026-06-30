'use client'

import type { NewsSourceMeta } from '@/utils/news'
import { Box } from '@outception-com/orbit/Box'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { PromotionFooter } from '../Promotions/PromotionFooter'
import { SwipeDeckCard } from './SwipeDeckCard'
import { useSwipeDeck } from './useSwipeDeck'

// One upcoming card peeks on the right, mirroring the previous card on the left.
const WINDOW_AHEAD = 1

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
}: {
  sources: NewsSourceMeta[]
  column: string
}) => {
  const items = sources.map((s) => s.id)
  const deck = useSwipeDeck(items, column)

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
  // The card currently in focus — its topic drives the promo banner below.
  const currentSource = byId.get(items[((deck.index % len) + len) % len])

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
        className="relative h-[52vh] min-h-[400px] w-full max-w-2xl overflow-hidden md:h-[62vh] md:min-h-[500px]"
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
              onSwipe={(move) =>
                move === 'next' ? deck.goNext() : deck.goPrev()
              }
            />
          )
        })}
      </motion.div>

      {/* Promo for the current card's topic, rendered BELOW the fixed-height
          deck so it extends the area instead of stealing news-list space. */}
      {currentSource ? (
        <div className="w-full max-w-2xl">
          <PromotionFooter topic={currentSource.column ?? null} />
        </div>
      ) : null}

      <div className="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-400">
        <button
          type="button"
          aria-label="Previous"
          disabled={!deck.canPrev}
          onClick={deck.goPrev}
          className={NAV_BUTTON}
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="inline-flex items-center gap-1 font-mono text-xs tabular-nums">
          <span className="inline-grid justify-items-end">
            <AnimatePresence initial={false} mode="popLayout">
              <motion.span
                key={deck.position}
                initial={{ y: 7, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -7, opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="col-start-1 row-start-1"
              >
                {deck.position}
              </motion.span>
            </AnimatePresence>
          </span>
          <span>/ {deck.total}</span>
        </span>
        <button
          type="button"
          aria-label="Next"
          disabled={!deck.canNext}
          onClick={deck.goNext}
          className={NAV_BUTTON}
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </Box>
  )
}
