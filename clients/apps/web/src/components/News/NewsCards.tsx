'use client'

import { useT } from '@/providers/translate'
import { Box } from '@outception-com/orbit/Box'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { motion } from 'motion/react'
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useSyncExternalStore,
  type KeyboardEvent,
} from 'react'
import { useIsMobileMedia } from '@/utils/mobile'
import { AutoplayControl } from './AutoplayControl'
import type { CardDescriptor } from './Card'
import { PEEK_X, PEEK_X_MOBILE, SwipeCard } from './SwipeCard'
import { useSwipeCards } from './useSwipeCards'
import {
  getFocusRequestServerSnapshot,
  getFocusRequestSnapshot,
  subscribe as subscribeNewsPrefs,
} from './newsPrefsStore'

// One upcoming card peeks on the right, mirroring the previous card on the left.
const WINDOW_AHEAD = 1

// Max pips shown at once. Small card sets show every card; larger card sets (e.g. the
// 60-source Trending card set) show a sliding window centred on the current card,
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
 * Swipeable card stack: the centred card follows the finger in any direction and
 * rotates, then commits on a fast flick OR a short drag, springing back below
 * the threshold. Swiping left/up advances, right/down goes back - the previous
 * and upcoming cards peek out behind. The arrows mirror this, and position
 * persists per column.
 */
export const NewsCards = ({
  cards: deck,
  column,
  initialActiveId,
  whyFor,
  storyId,
  onActiveChange,
}: {
  cards: CardDescriptor[]
  column: string
  initialActiveId?: string
  /** The "why this card" line for an id, when there is one. */
  whyFor?: (id: string) => string | null | undefined
  /** A shared story to open on the card that holds it. */
  storyId?: string | null
  /** The id on top, whenever it changes. */
  onActiveChange?: (id: string) => void
}) => {
  // Memoised: a fresh array each render re-creates `move` and re-fires both of
  // useSwipeCards's effects on every repaint, remeasuring the card set as you type.
  const t = useT()
  const items = useMemo(() => deck.map((c) => c.id), [deck])
  const focusRequest = useSyncExternalStore(
    subscribeNewsPrefs,
    getFocusRequestSnapshot,
    getFocusRequestServerSnapshot,
  )
  const cards = useSwipeCards(items, column, initialActiveId, focusRequest)
  const { goNext, goPrev, goTo } = cards
  const deckRef = useRef<HTMLDivElement>(null)
  const onSwipe = useCallback(
    (move: 'next' | 'prev') => (move === 'next' ? goNext() : goPrev()),
    [goNext, goPrev],
  )
  // English only: kept as a flag so the swipe geometry stays direction-aware.
  const rtl = false
  const activeId = items[cards.index]
  useEffect(() => {
    if (activeId) onActiveChange?.(activeId)
  }, [activeId, onActiveChange])
  // The arrow keys move the deck when it has focus: the forward key follows
  // the script direction like the swipe does.
  const onKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      const advance = rtl ? e.key === 'ArrowLeft' : e.key === 'ArrowRight'
      e.preventDefault()
      if (advance) goNext()
      else goPrev()
    },
    [goNext, goPrev, rtl],
  )
  // Resolved once here rather than per card: one media listener, and no
  // per-card post-mount flip that made the peeks jump on first paint.
  const peekX = useIsMobileMedia() ? PEEK_X_MOBILE : PEEK_X
  // Under dir="rtl" the flex nav row auto-reverses (Previous ends up on the
  // right), so the chevrons must swap to keep pointing the way the card set moves.
  const PrevIcon = rtl ? ChevronRight : ChevronLeft
  const NextIcon = rtl ? ChevronLeft : ChevronRight

  if (!deck.length) return null

  const byId = new Map(deck.map((c) => [c.id, c]))
  // Mounted window: the previous card (peeking left), the current one, and the
  // next card(s) peeking right. Indices wrap so the card set loops - at the last
  // card the upcoming peek is the first card, and vice versa. Keyed by id so
  // each card keeps its node and glides between slots as the index moves. With
  // very few cards we trim the offsets to keep every id (and React key) unique.
  const len = items.length
  const offsets =
    len > 2 ? [-1, 0, WINDOW_AHEAD] : len === 2 ? [0, WINDOW_AHEAD] : [0]
  const windowed = offsets.map((depth) => ({
    id: items[(((cards.index + depth) % len) + len) % len],
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
        ref={deckRef}
        key={column}
        initial={{ opacity: 0, y: 18, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ type: 'spring', stiffness: 260, damping: 30 }}
        // Desktop: no clipping - the neighbouring sheets are fully visible,
        // poking out past the card set with their real edges and tilt, like papers
        // spread on a desk. Mobile clips, since the card set is the screen's
        // full width there and overflow would scroll sideways: the screen's
        // own edge is the cut, with no fade that eats the card's edges.
        className="cards-viewport relative min-h-[max(min(540px,62svh),calc(100svh-18rem))] w-full max-w-2xl overflow-x-clip md:min-h-[560px] md:overflow-x-visible"
        role="region"
        aria-label={t('news.cards.deck')}
        tabIndex={0}
        onKeyDown={onKeyDown}
        data-testid="card-deck"
      >
        {windowed.map(({ id, depth }) => {
          const card = byId.get(id)
          if (!card) return null
          return (
            <SwipeCard
              key={id}
              card={card}
              depth={depth}
              canNext={cards.canNext}
              canPrev={cards.canPrev}
              peekX={peekX}
              rtl={rtl}
              onSwipe={onSwipe}
              why={whyFor?.(id)}
              storyId={storyId}
            />
          )
        })}
      </motion.div>

      <div className="flex items-center gap-4 text-sm text-neutral-500 dark:text-neutral-400">
        <button
          type="button"
          aria-label={t('news.cards.previous')}
          disabled={!cards.canPrev}
          onClick={cards.goPrev}
          className={NAV_BUTTON}
        >
          <PrevIcon className="h-4 w-4" />
        </button>
        {/* Every card set - small or the 60-source Trending card set - reads as the
            same windowed pip strip: dots with the current card as a wider
            pill. No numeric readout. The visually-hidden live region keeps the
            position available to assistive tech without showing a number. */}
        <span className="flex items-center gap-1.5">
          <span className="sr-only" aria-live="polite">
            {cards.position} / {cards.total}
          </span>
          {pipWindow(cards.position, cards.total).map((i) => (
            <span
              key={i}
              aria-hidden
              className={
                i === cards.position
                  ? 'ink-fill h-1.5 w-5 rounded-full opacity-80 transition-all duration-300'
                  : 'ink-fill h-1.5 w-1.5 rounded-full opacity-25 transition-all duration-300'
              }
            />
          ))}
        </span>
        <button
          type="button"
          aria-label={t('news.cards.next')}
          disabled={!cards.canNext}
          onClick={cards.goNext}
          className={NAV_BUTTON}
        >
          <NextIcon className="h-4 w-4" />
        </button>
        <AutoplayControl
          cardIds={items}
          index={cards.index}
          goTo={goTo}
          interactionRef={deckRef}
        />
      </div>
    </Box>
  )
}
