import type { NewsSourceMeta } from '@/hooks/outception/news'
import { WEATHER_SOURCE_ID } from '@/utils/weather'
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
import { WeatherCard } from './WeatherCard'

type DeckMove = 'next' | 'prev'
type Dir = 'left' | 'right' | 'up' | 'down'

// Swipe physics (mobile). Smaller peek + tilt than web since the screen is
// narrower and the neighbours only barely poke out behind the front card.
const PEEK_X = 40
const SCALE = [1, 0.92, 0.85]
const MAX_ROTATE = 8 // deg — max tilt at the edge of a horizontal drag
const PEEK_TILT = 2.5 // deg — resting tilt of the peeking stack
const SWIPE_THRESHOLD = 80 // px along the dominant axis to commit
const VELOCITY_TRIGGER = 500 // px/s — a flick this fast commits
const ROTATE_DIVISOR = 320 // approx card width, to scale the drag pivot

const spring = { damping: 26, stiffness: 260 }

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
  const rtlSign = rtl ? -1 : 1
  const slot = slotFor(depth, rtlSign)
  const isTop = depth === 0

  const tx = useSharedValue(slot.x)
  const ty = useSharedValue(0)
  const sc = useSharedValue(slot.scale)
  const rot = useSharedValue(slot.rotate)

  // Glide to this depth's resting slot whenever the depth (or direction) changes.
  useEffect(() => {
    tx.value = withSpring(slot.x, spring)
    ty.value = withSpring(0, spring)
    sc.value = withSpring(slot.scale, spring)
    rot.value = withSpring(slot.rotate, spring)
  }, [depth, rtlSign, slot.x, slot.scale, slot.rotate, tx, ty, sc, rot])

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
    .onUpdate((e) => {
      tx.value = e.translationX
      ty.value = e.translationY
      const clamped = Math.max(-1, Math.min(e.translationX / ROTATE_DIVISOR, 1))
      rot.value = rtlSign * clamped * MAX_ROTATE
    })
    .onEnd((e) => {
      const horiz = Math.abs(e.translationX) >= Math.abs(e.translationY)
      const offset = horiz ? e.translationX : e.translationY
      const vel = horiz ? e.velocityX : e.velocityY
      const committed =
        Math.abs(offset) > SWIPE_THRESHOLD || Math.abs(vel) > VELOCITY_TRIGGER
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
        style={[StyleSheet.absoluteFill, { zIndex: slot.z }, animatedStyle]}
      >
        {source.id === WEATHER_SOURCE_ID ? (
          <WeatherCard source={source} />
        ) : (
          <NewsSourceCard source={source} />
        )}
      </Animated.View>
    </GestureDetector>
  )
}
