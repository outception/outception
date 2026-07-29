import * as Haptics from 'expo-haptics'
import type { NewsSourceMeta } from '@/hooks/outception/news'
import {
  getSummaryOpenSnapshot,
  setSummarySwipeHandler,
  subscribeSummaryOpen,
} from '@/utils/summaryOpen'
import { memo, useEffect, useSyncExternalStore } from 'react'
import { StyleSheet } from 'react-native'
import { Gesture, GestureDetector } from 'react-native-gesture-handler'
import Animated, {
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
} from 'react-native-reanimated'
import { GameCard, isMiniGameId } from './GameCard'
import { HeatmapCard } from './HeatmapCard'
import { NewsSourceCard } from './NewsSourceCard'

// Game cards swipe only from the header strip (badge + title row) - the
// board below belongs to the game itself.
const GAME_DRAG_HANDLE_H = 88

type DeckMove = 'next' | 'prev'
type Dir = 'left' | 'right' | 'up' | 'down'

// Swipe physics (mirroring the web SwipeDeckCard). Smaller peek than web
// desktop since the screen is narrower and the neighbours only barely poke out.
const PEEK_X = 24
const SCALE = [1, 0.9, 0.82]
const MAX_ROTATE = 16 // deg - max tilt at the edge of a horizontal drag
const PEEK_TILT = 2.5 // deg - resting tilt of the peeking stack
const DISTANCE_RATIO = 0.22 // commit once dragged ~1/5 of the card along that axis
// …but never ask for more than this. The web ratio is comfortable because the
// card is small inside the window; on a phone the card fills the screen, so
// 22% of it is a ~230px drag - far more than a natural flick, which made the
// deck feel unresponsive.
const MAX_COMMIT_DISTANCE = 90 // px
const VELOCITY_TRIGGER = 500 // px/s - a flick this fast commits

const spring = { damping: 26, stiffness: 260 }

/** Deterministic per-source jitter (±0.8°) layered on the resting tilt, so the
 * pile reads as naturally tossed rather than machine-fanned - same hash as web. */
const jitterFor = (id: string) => {
  let hash = 0
  for (const ch of id) hash = (hash * 31 + ch.charCodeAt(0)) | 0
  return ((((hash % 100) + 100) % 100) / 100 - 0.5) * 1.6
}

type Slot = { x: number; scale: number; rotate: number; z: number }

/** Resting transform for a card at a given depth: 0 = centred/top, positive =
 * the upcoming stack, negative = the previous card. The upcoming stack peeks on
 * the side the deck advances toward - right in LTR, mirrored to the left in RTL
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

// Memoized so parent deck re-renders (follow toggles, failed-source updates)
// don't re-create the pan gesture + worklets and re-render the card subtree.
// Effective only while every prop is stable - NewsDeck passes a ref-backed
// `onSwipe` for exactly this reason.
export const SwipeDeckCard = memo(function SwipeDeckCard({
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
}) {
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
  // +1 if grabbed in the top half, -1 in the bottom - so the card pivots
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
    if (move) {
      // A light tick as the card commits - the tactile "page turn".
      void Haptics.selectionAsync()
      onSwipe(move)
      return
    }
    tx.value = withSpring(0, spring)
    ty.value = withSpring(0, spring)
    rot.value = withSpring(0, spring)
  }

  // The open summary detects horizontal strokes itself (cross-component
  // gesture blocking is unreliable on iOS) and calls this with the stroke's
  // dx; the deck applies its own direction, RTL and bounds rules.
  useEffect(() => {
    if (!isTop) return
    setSummarySwipeHandler((dx: number) => {
      const dir: Dir = dx < 0 ? 'left' : 'right'
      if (isNextDir(dir, rtl) && canNext) settle('next')
      else if (!isNextDir(dir, rtl) && canPrev) settle('prev')
    })
    return () => setSummarySwipeHandler(null)
  })

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

  // While an inline summary is open on the top card the deck goes
  // HORIZONTAL-ONLY rather than dead: a vertical drag belongs to the
  // summary's ScrollView (the pan used to steal it and fling the card away
  // mid-read), but a sideways swipe is still how you leave a card, and
  // disabling the pan outright stranded readers on an open summary.
  const summaryOpen = useSyncExternalStore(
    subscribeSummaryOpen,
    getSummaryOpenSnapshot,
    getSummaryOpenSnapshot,
  )

  // BOTH tests, like the web (which keys off its own MINI_GAMES map): the
  // server calling a source a game isn't enough - without a page shipped for
  // that id the card would mount a WebView on a 404, so an unknown id falls
  // through to the ordinary news card.
  const isGame = source.type === 'game' && isMiniGameId(source.id)

  const pan = Gesture.Pan()
    .enabled(isTop)
    // Game cards: touches on the board belong to the game (taps, the cube's
    // rotation drags) - the deck swipes only from the header strip, exactly
    // like the web where the iframe owns its pointer events.
    .hitSlop(isGame ? { top: 0, height: GAME_DRAG_HANDLE_H } : {})
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
  if (summaryOpen) {
    // Applied only in this state (the builder mutates and returns itself):
    // the pan must lose vertical movement to the summary's ScrollView and
    // claim horizontal, so a reader can still swipe to the next card with a
    // summary open instead of being stranded until they close it.
    // 10/22, not 14/10: real thumb swipes ARC. With fail at 10 vertical px,
    // an ordinary stroke banked 10px of drift before reaching 14px of
    // travel and the pan killed itself - swiping only worked after closing
    // the summary (which drops these constraints). Horizontal now activates
    // sooner than vertical can fail it; a deliberate scroll still runs
    // vertical past 22px long before 10px of sideways travel.
    pan.activeOffsetX([-10, 10]).failOffsetY([-22, 22])
    // Offsets alone were not enough on iOS: the scroll view starts panning on
    // ANY direction of movement and wins the race before 14 horizontal px
    // accumulate. Blocking it makes it WAIT for the pan's verdict - the pan
    // fails within 10 vertical px, so scrolling starts imperceptibly late,
    // and a horizontal stroke now belongs to the deck.
  }

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
        {source.type === 'heatmap' ? (
          <HeatmapCard source={source} elevated={isTop} />
        ) : isGame ? (
          <GameCard source={source} elevated={isTop} />
        ) : (
          <NewsSourceCard source={source} elevated={isTop} />
        )}
      </Animated.View>
    </GestureDetector>
  )
})
