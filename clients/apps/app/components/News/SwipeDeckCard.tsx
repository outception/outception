import type { NewsSourceMeta } from '@/hooks/outception/news'
import { useEffect } from 'react'
import { StyleSheet } from 'react-native'
import { Gesture, GestureDetector } from 'react-native-gesture-handler'
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated'
import { NewsSourceCard } from './NewsSourceCard'

type DeckMove = 'next' | 'prev'
type Dir = 'left' | 'right' | 'up' | 'down'

// Swipe physics (mirroring the web SwipeDeckCard). Smaller peek than web
// desktop since the screen is narrower and the neighbours only barely poke out.
const PEEK_X = 24
const SCALE = [1, 0.9, 0.82]
const MAX_ROTATE = 16 // deg — max tilt at the edge of a horizontal drag
const PEEK_TILT = 2.5 // deg — resting tilt of the peeking stack
const DISTANCE_RATIO = 0.22 // commit once dragged ~1/5 of the card along that axis
// …but never ask for more than this. The web ratio is comfortable because the
// card is small inside the window; on a phone the card fills the screen, so
// 22% of it is a ~230px drag — far more than a natural flick, which made the
// deck feel unresponsive.
const MAX_COMMIT_DISTANCE = 90 // px
const VELOCITY_TRIGGER = 500 // px/s — a flick this fast commits

const spring = { damping: 26, stiffness: 260 }

/** Deterministic per-source jitter (±0.8°) layered on the resting tilt, so the
 * pile reads as naturally tossed rather than machine-fanned — same hash as web. */
const jitterFor = (id: string) => {
  let hash = 0
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) | 0
  return ((((hash % 100) + 100) % 100) / 100 - 0.5) * 1.6
}

type Slot = { x: number; scale: number; rotate: number; z: number }

/** Resting transform for a card at a given depth: 0 = centred/top, positive =
 * the upcoming stack, negative = the previous card. The upcoming stack peeks on
 * the side the deck advances toward — right in LTR, mirrored to the left in RTL
 * (`rtlSign` is -1 for RTL). */
const slotFor = (depth: number, rtlSign: number): Slot => {
  if (depth === 0) return { x: 0, scale: 1, rotate: 0, z: 30 }
  if (depth < 0)
    return { x: rtlSign * -PEEK_X, scale: SCALE[1], rotate: -PEEK_TILT, z: 10 }
  return {
    x: rtlSign * PEEK_X * depth,
    scale: SCALE[depth] ?? 0.8,
    rotate: PEEK_TILT * depth,
    z: 30 - depth,
  }
}

// Up always advances; horizontally, the "forward" side mirrors with the script:
// left advances in LTR, right advances in RTL. The opposite side (and down)
// goes back.
const isNextDir = (d: Dir, rtl: boolean) =>
  d === 'up' || d === (rtl ? 'right' : 'left')

export const SwipeDeckCard = ({
  source,
  depth,
  canNext,
  canPrev,
  rtl = false,
  bottomInset = 0,
  onSwipe,
}: {
  source: NewsSourceMeta
  /** 0 = centred/interactive; >0 = upcoming peek stack; <0 = previous peek. */
  depth: number
  canNext: boolean
  canPrev: boolean
  /** Right-to-left locale: mirror the peek sides, tilt, and swipe direction. */
  rtl?: boolean
  /** Strip left free below the card (the deck's ad banner sits there). */
  bottomInset?: number
  onSwipe: (move: DeckMove) => void
}) => {
  const rtlSign = rtl ? -1 : 1
  const slot = slotFor(depth, rtlSign)
  const isTop = depth === 0
  // The top card always squares up to 0°; only the peeking pile jitters.
  const restRotate = slot.rotate + (isTop ? 0 : jitterFor(source.id))

  const tx = useSharedValue(slot.x)
  const ty = useSharedValue(0)
  const sc = useSharedValue(slot.scale)
  const rot = useSharedValue(restRotate)
  // Measured card box: the drag pivot scales with the real width and the
  // commit distance with the real height, like the web's getBoundingClientRect.
  const cardW = useSharedValue(320)
  const cardH = useSharedValue(480)
  // +1 if grabbed in the top half, -1 in the bottom — so the card pivots
  // around the hand like a real thrown card.
  const grabDirY = useSharedValue(1)

  // Glide to this depth's resting slot whenever the depth (or direction) changes.
  useEffect(() => {
    tx.value = withSpring(slot.x, spring)
    ty.value = withSpring(0, spring)
    sc.value = withSpring(slot.scale, spring)
    rot.value = withSpring(restRotate, spring)
  }, [depth, rtlSign, slot.x, slot.scale, restRotate, tx, ty, sc, rot])

  const settle = (move: DeckMove | null) => {
    if (move) onSwipe(move)
    else {
      tx.value = withSpring(0, spring)
      ty.value = withSpring(0, spring)
      rot.value = withSpring(0, spring)
    }
  }

  const commit = (horiz: boolean, ox: number, oy: number) => {
    const dir: Dir = horiz
      ? ox < 0
        ? 'left'
        : 'right'
      : oy < 0
        ? 'up'
        : 'down'
    if (isNextDir(dir, rtl) && canNext) settle('next')
    else if (!isNextDir(dir, rtl) && canPrev) settle('prev')
    else settle(null)
  }

  const pan = Gesture.Pan()
    .enabled(isTop)
    .onBegin((e) => {
      grabDirY.value = e.y < cardH.value / 2 ? 1 : -1
    })
    .onUpdate((e) => {
      tx.value = e.translationX
      ty.value = e.translationY
      const clamped = Math.max(-1, Math.min(e.translationX / cardW.value, 1))
      rot.value = rtlSign * grabDirY.value * clamped * MAX_ROTATE
    })
    .onEnd((e) => {
      const horiz = Math.abs(e.translationX) >= Math.abs(e.translationY)
      const offset = horiz ? e.translationX : e.translationY
      const vel = horiz ? e.velocityX : e.velocityY
      const reach = horiz ? cardW.value : cardH.value
      const threshold = Math.min(reach * DISTANCE_RATIO, MAX_COMMIT_DISTANCE)
      const committed =
        Math.abs(offset) > threshold || Math.abs(vel) > VELOCITY_TRIGGER
      if (committed) runOnJS(commit)(horiz, e.translationX, e.translationY)
      else runOnJS(settle)(null)
    })

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: tx.value },
      { translateY: ty.value },
      { scale: sc.value },
      { rotate: `${rot.value}deg` },
    ],
  }))

  return (
    <GestureDetector gesture={pan}>
      <Animated.View
        pointerEvents={isTop ? 'auto' : 'none'}
        onLayout={(e) => {
          cardW.value = e.nativeEvent.layout.width
          cardH.value = e.nativeEvent.layout.height
        }}
        // Side inset (web uses `right-5 left-5`) so the peeking neighbours
        // stay on screen beside the front card instead of sitting half off it.
        style={[
          StyleSheet.absoluteFill,
          { left: 20, right: 20, bottom: bottomInset, zIndex: slot.z },
          animatedStyle,
        ]}
      >
        <NewsSourceCard source={source} elevated={isTop} />
      </Animated.View>
    </GestureDetector>
  )
}
