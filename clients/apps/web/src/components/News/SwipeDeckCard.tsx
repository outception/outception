'use client'

import type { NewsSourceMeta } from '@/utils/news'
import useIsMobile from '@/utils/mobile'
import { animate, motion, useMotionValue, useTransform } from 'motion/react'
import type { PanInfo } from 'motion/react'
import { useEffect, useRef, type PointerEvent } from 'react'
import { NewsSourceCard } from './NewsSourceCard'

type DeckMove = 'next' | 'prev'
type Dir = 'left' | 'right' | 'up' | 'down'

// Swipe physics:
const MAX_ROTATE = 16 // deg — max tilt at the edge of a horizontal drag
const DISTANCE_RATIO = 0.22 // commit once dragged ~1/5 of the card along that axis
const VELOCITY_TRIGGER = 500 // px/s — a flick this fast commits
const RESET = { type: 'spring', stiffness: 300, damping: 30 } as const

// Peek layout: the previous card peeks left, the upcoming cards peek right.
// Mobile uses a much smaller peek so the neighbours barely poke out behind the
// front card (which stays the focus on a narrow screen).
const PEEK_X = 72
const PEEK_X_MOBILE = 24
const SCALE = [1, 0.9, 0.82]

const cardWidth = (el: HTMLElement | null) => el?.offsetWidth || 600
const cardHeight = (el: HTMLElement | null) => el?.offsetHeight || 600

type Slot = { x: number; y: number; scale: number; z: number }
/** Resting transform for a card at a given depth: 0 = centred/top, positive =
 * upcoming stack (peeking right), negative = the previous card (peeking left). */
const slotFor = (depth: number, peekX: number): Slot => {
  if (depth === 0) return { x: 0, y: 0, scale: 1, z: 30 }
  if (depth < 0) return { x: -peekX, y: 0, scale: SCALE[1], z: 10 }
  return { x: peekX * depth, y: 0, scale: SCALE[depth] ?? 0.78, z: 30 - depth }
}

// Left and up advance; right and down go back.
const isNextDir = (d: Dir) => d === 'left' || d === 'up'

export const SwipeDeckCard = ({
  source,
  depth,
  canNext,
  canPrev,
  onSwipe,
}: {
  source: NewsSourceMeta
  /** 0 = centred/interactive; >0 = upcoming peek stack; <0 = previous peek. */
  depth: number
  canNext: boolean
  canPrev: boolean
  onSwipe: (move: DeckMove) => void
}) => {
  const el = useRef<HTMLDivElement>(null)
  const { isMobile } = useIsMobile()
  const peekX = isMobile ? PEEK_X_MOBILE : PEEK_X
  const slot = slotFor(depth, peekX)
  const x = useMotionValue(slot.x)
  const y = useMotionValue(slot.y)
  const scale = useMotionValue(slot.scale)
  const isTop = depth === 0
  // +1 if grabbed in the top half, -1 in the bottom — so the card pivots around
  // the hand like a real thrown card.
  const grabDirY = useRef(1)

  const rotate = useTransform(
    x,
    (v) =>
      grabDirY.current *
      Math.max(-1, Math.min(v / cardWidth(el.current), 1)) *
      MAX_ROTATE,
  )

  // Glide to this depth's resting slot whenever the depth (or peek) changes.
  useEffect(() => {
    const s = slotFor(depth, peekX)
    const cx = animate(x, s.x, RESET)
    const cy = animate(y, s.y, RESET)
    const cs = animate(scale, s.scale, RESET)
    return () => {
      cx.stop()
      cy.stop()
      cs.stop()
    }
  }, [depth, peekX, x, y, scale])

  const onPointerDown = (e: PointerEvent) => {
    const rect = el.current?.getBoundingClientRect()
    if (rect) grabDirY.current = e.clientY < rect.top + rect.height / 2 ? 1 : -1
  }

  // The whole card is the swipe surface — it drags freely in any direction and
  // commits on the dominant axis: left/up advances, right/down goes back. The
  // card itself never scrolls (its list is clipped, not scrollable), so a drag
  // is never ambiguous with an inner scroll.
  const onDragEnd = (_: unknown, info: PanInfo) => {
    const { x: ox, y: oy } = info.offset
    const horiz = Math.abs(ox) >= Math.abs(oy)
    const dir: Dir = horiz
      ? ox < 0
        ? 'left'
        : 'right'
      : oy < 0
        ? 'up'
        : 'down'
    const reach = horiz ? cardWidth(el.current) : cardHeight(el.current)
    const offset = horiz ? ox : oy
    const vel = horiz ? info.velocity.x : info.velocity.y
    const committed =
      Math.abs(offset) > reach * DISTANCE_RATIO ||
      Math.abs(vel) > VELOCITY_TRIGGER
    if (committed && isNextDir(dir) && canNext) onSwipe('next')
    else if (committed && !isNextDir(dir) && canPrev) onSwipe('prev')
    else {
      animate(x, 0, RESET)
      animate(y, 0, RESET)
    }
  }

  return (
    <motion.div
      ref={el}
      // The wrapper owns the card's glass surface; the inner card renders bare.
      // The front card uses the denser glass (glass-pop-strong) so it mostly
      // veils the peeking cards stacked behind it; the peeks use glass-pop-peek
      // (lighter, no drop shadow so they don't halo out behind the front card).
      className={`${
        isTop ? 'glass-pop-strong' : 'glass-pop-peek'
      } absolute inset-y-0 right-5 left-5 overflow-hidden rounded-3xl md:right-14 md:left-14`}
      style={{ x, y, rotate, scale, zIndex: slot.z, touchAction: 'none' }}
      drag={isTop}
      dragMomentum={false}
      onPointerDown={isTop ? onPointerDown : undefined}
      onDragEnd={isTop ? onDragEnd : undefined}
    >
      <NewsSourceCard source={source} />
    </motion.div>
  )
}
