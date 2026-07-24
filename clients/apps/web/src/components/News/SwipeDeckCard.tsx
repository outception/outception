'use client'

import type { NewsSourceMeta } from '@/utils/news'
import { WEATHER_SOURCE_ID } from '@/utils/weather'
import useIsMobile from '@/utils/mobile'
import { animate, motion, useMotionValue, useTransform } from 'motion/react'
import type { PanInfo } from 'motion/react'
import { useEffect, useRef, type PointerEvent } from 'react'
import { NewsSourceCard } from './NewsSourceCard'
import { WeatherCard } from './WeatherCard'

type DeckMove = 'next' | 'prev'
type Dir = 'left' | 'right' | 'up' | 'down'

// Swipe physics:
const MAX_ROTATE = 16 // deg — max tilt at the edge of a horizontal drag
const DISTANCE_RATIO = 0.22 // commit once dragged ~1/5 of the card along that axis
const VELOCITY_TRIGGER = 500 // px/s — a flick this fast commits
const RESET = { type: 'spring', stiffness: 300, damping: 30 } as const

// Peek layout: the previous card peeks left, the upcoming cards peek right.
// Desktop shows a modest sliver of each neighbour — enough to read the stack
// without stealing attention from the front page (the sheets render whole,
// unclipped; see NewsDeck). Mobile uses a much smaller peek so the
// neighbours barely poke out behind the front card.
const PEEK_X = 56
const PEEK_X_MOBILE = 24
const SCALE = [1, 0.9, 0.82]
// Peeking sheets rest slightly rotated — a stack of tossed papers rather than
// a perfectly squared pile. The top card always squares up to 0°.
const PEEK_TILT = 2.5 // deg

const cardWidth = (el: HTMLElement | null) => el?.offsetWidth || 600
const cardHeight = (el: HTMLElement | null) => el?.offsetHeight || 600

type Slot = { x: number; y: number; scale: number; z: number; tilt: number }
/** Resting transform for a card at a given depth: 0 = centred/top, positive =
 * the upcoming stack, negative = the previous card. The upcoming stack peeks on
 * the side the deck advances toward — right in LTR, mirrored to the left in RTL
 * (`rtlSign` is -1 for RTL) so the spatial model matches the reader's script. */
const slotFor = (depth: number, peekX: number, rtlSign: number): Slot => {
  if (depth === 0) return { x: 0, y: 0, scale: 1, z: 30, tilt: 0 }
  if (depth < 0)
    return {
      x: rtlSign * -peekX,
      y: 0,
      scale: SCALE[1],
      z: 10,
      tilt: -PEEK_TILT,
    }
  return {
    x: rtlSign * peekX * depth,
    y: 0,
    scale: SCALE[depth] ?? 0.78,
    z: 30 - depth,
    tilt: PEEK_TILT * depth,
  }
}

// Up always advances; horizontally, the "forward" side mirrors with the script:
// left advances in LTR, right advances in RTL. The opposite side (and down) goes
// back.
const isNextDir = (d: Dir, rtl: boolean) =>
  d === 'up' || d === (rtl ? 'right' : 'left')

const isTopDepth = (depth: number) => depth === 0

export const SwipeDeckCard = ({
  source,
  depth,
  canNext,
  canPrev,
  rtl = false,
  onSwipe,
}: {
  source: NewsSourceMeta
  /** 0 = centred/interactive; >0 = upcoming peek stack; <0 = previous peek. */
  depth: number
  canNext: boolean
  canPrev: boolean
  /** Right-to-left locale: mirror the peek sides, tilt, and swipe direction. */
  rtl?: boolean
  onSwipe: (move: DeckMove) => void
}) => {
  const el = useRef<HTMLDivElement>(null)
  const { isMobile } = useIsMobile()
  const peekX = isMobile ? PEEK_X_MOBILE : PEEK_X
  const rtlSign = rtl ? -1 : 1
  const slot = slotFor(depth, peekX, rtlSign)
  // Deterministic per-source jitter (±0.8°) layered on the resting tilt, so
  // the pile reads as naturally tossed rather than machine-fanned.
  let hash = 0
  for (const ch of source.id) hash = (hash * 31 + ch.charCodeAt(0)) | 0
  const jitter = ((((hash % 100) + 100) % 100) / 100 - 0.5) * 1.6

  const x = useMotionValue(slot.x)
  const y = useMotionValue(slot.y)
  const scale = useMotionValue(slot.scale)
  const tilt = useMotionValue(slot.tilt + (isTopDepth(depth) ? 0 : jitter))
  const isTop = depth === 0
  // +1 if grabbed in the top half, -1 in the bottom — so the card pivots around
  // the hand like a real thrown card.
  const grabDirY = useRef(1)

  const dragRotate = useTransform(
    x,
    (v) =>
      rtlSign *
      grabDirY.current *
      Math.max(-1, Math.min(v / cardWidth(el.current), 1)) *
      MAX_ROTATE,
  )
  // Resting tilt (the tossed-stack look) plus the drag-driven pivot.
  const rotate = useTransform(() => tilt.get() + dragRotate.get())

  // Glide to this depth's resting slot whenever the depth (or peek) changes.
  useEffect(() => {
    const s = slotFor(depth, peekX, rtlSign)
    const cx = animate(x, s.x, RESET)
    const cy = animate(y, s.y, RESET)
    const cs = animate(scale, s.scale, RESET)
    const ct = animate(tilt, s.tilt + (depth === 0 ? 0 : jitter), RESET)
    return () => {
      cx.stop()
      cy.stop()
      cs.stop()
      ct.stop()
    }
  }, [depth, peekX, rtlSign, x, y, scale, tilt, jitter])

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
    if (committed && isNextDir(dir, rtl) && canNext) onSwipe('next')
    else if (committed && !isNextDir(dir, rtl) && canPrev) onSwipe('prev')
    else {
      animate(x, 0, RESET)
      animate(y, 0, RESET)
    }
  }

  return (
    <motion.div
      ref={el}
      // The wrapper owns the card's paper surface; the inner card renders bare.
      // The front card is the top sheet of the pile (paper-sheet: strong ink
      // rule + offset shadow); the peeks use paper-sheet-peek (rule only, no
      // drop shadow so they don't halo out behind the front card).
      className={`${
        isTop ? 'paper-sheet' : 'paper-sheet-peek'
      } absolute inset-y-0 right-5 left-5 overflow-hidden rounded-2xl md:right-14 md:left-14`}
      // Peeking neighbours are scenery: inert to the pointer and hidden from
      // assistive tech, so their buttons/links can't be activated through the
      // exposed slivers behind the front card.
      style={{
        x,
        y,
        rotate,
        scale,
        zIndex: slot.z,
        touchAction: 'none',
        pointerEvents: isTop ? 'auto' : 'none',
      }}
      aria-hidden={!isTop}
      drag={isTop}
      dragMomentum={false}
      onPointerDown={isTop ? onPointerDown : undefined}
      onDragEnd={isTop ? onDragEnd : undefined}
    >
      {/* Section color-coding: the source's accent color as a short rounded
          tab hanging from the sheet's top-left edge — quieter than a full
          stripe. (Plain div: the color is a dynamic per-source value, which
          Box's token-only backgroundColor can't take — AGENTS.md escape
          hatch.) */}
      <div
        aria-hidden
        className="absolute top-0 left-6 z-10 h-1 w-10 rounded-b-full opacity-90"
        style={{ backgroundColor: source.color }}
      />
      {source.id === WEATHER_SOURCE_ID ? (
        <WeatherCard source={source} />
      ) : (
        <NewsSourceCard source={source} />
      )}
    </motion.div>
  )
}
