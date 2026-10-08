import LogoIcon, { BRAND_RAMPS } from '@/components/Shared/OutceptionLogo'
import {
  getEditionSnapshot,
  subscribeEdition,
} from '@/design-system/themeStore'
import { Touchable } from '@/components/Shared/Touchable'
import MaskedView from '@react-native-masked-view/masked-view'
import { LinearGradient } from 'expo-linear-gradient'
import { useState, useSyncExternalStore } from 'react'
import { Image, View } from 'react-native'
import Animated, {
  Easing,
  runOnJS,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated'

// Frame count of assets/brand/top-spin.webp - the SAME sprite the web uses
// (clients/apps/web/public/assets/brand/top-spin.webp). Must match the strip.
const SPIN_FRAMES = 36
const SPIN_MS = 1200

// Web builds this fill from the EDITION's brand ramp (--color-brand-200…900),
// so the spinning top is always the mark's current colour. Hard-coding red made
// it flash red on phosphor, tide, dune and neon.
const SPIN_LOCATIONS = [0, 0.34, 0.46, 0.5, 0.54, 0.7, 1]

// Ramp indices are 0-based over [100…900], so brand-200 is index 1.
const spinGradient = (ramp: readonly string[]): string[] => [
  ramp[1],
  ramp[3],
  ramp[4],
  ramp[8],
  ramp[6],
  ramp[4],
  ramp[2],
]

/** One frame of the sprite strip, masked over the edition's brand gradient -
 * the shared guts of the tap-to-spin mark. */
const SpinSprite = ({
  size,
  frame,
  ramp,
}: {
  size: number
  frame: SharedValue<number>
  ramp: readonly string[]
}) => {
  const stripStyle = useAnimatedStyle(() => {
    const step = Math.min(Math.floor(frame.value), SPIN_FRAMES - 1)
    // `reverse` on the web: start at the last frame and walk backwards.
    return { transform: [{ translateX: -(SPIN_FRAMES - 1 - step) * size }] }
  })

  return (
    // eslint-disable-next-line @outception/no-view -- raw clip box for the sprite strip
    <View style={{ width: size, height: size, overflow: 'hidden' }}>
      <MaskedView
        // REQUIRED on Android: the default `hardware` mode rasterizes the
        // mask into a bitmap once at attach and never re-reads it, so an
        // animated mask shows a single frozen frame. `software` re-draws
        // it each frame. iOS ignores this.
        androidRenderingMode="software"
        style={{ width: size, height: size }}
        maskElement={
          <Animated.View style={[{ width: size, height: size }, stripStyle]}>
            {/* eslint-disable-next-line @outception/no-image -- MaskedView needs a
                plain RN Image for alpha compositing; expo-image does not
                composite as a mask on Android. */}
            <Image
              source={require('../../assets/brand/top-spin.webp')}
              style={{ width: SPIN_FRAMES * size, height: size }}
              resizeMode="stretch"
            />
          </Animated.View>
        }
      >
        <LinearGradient
          colors={spinGradient(ramp) as [string, string, ...string[]]}
          locations={SPIN_LOCATIONS as [number, number, ...number[]]}
          style={{ width: size, height: size }}
        />
      </MaskedView>
    </View>
  )
}

const useBrandRamp = (): readonly string[] => {
  const edition = useSyncExternalStore(
    subscribeEdition,
    getEditionSnapshot,
    getEditionSnapshot,
  )
  return BRAND_RAMPS[edition] ?? BRAND_RAMPS.ruby
}

/**
 * The wall's brand mark: tapping it cycles the theme edition and plays the
 * pre-rendered 3D spinning-top animation.
 *
 * This is the web animation rather than an approximation: the same 36-frame
 * sprite, stepped at the same rate over the same 1.2s, played in REVERSE so the
 * top turns right-to-left, used as an alpha MASK over the same vertical
 * gradient. CSS animates `mask-position` with `steps(36)`; here that becomes a
 * whole-frame translateX of the strip, with MaskedView supplying the masking.
 */
export const SpinningLogo = ({
  size,
  onPress,
  accessibilityLabel,
}: {
  size: number
  onPress: () => void
  accessibilityLabel: string
}) => {
  const ramp = useBrandRamp()
  const [spinning, setSpinning] = useState(false)
  // Whole frames only - CSS uses steps(36), so the sprite must jump frame to
  // frame rather than slide continuously.
  const frame = useSharedValue(0)

  const spin = () => {
    if (!spinning) {
      setSpinning(true)
      frame.value = 0
      frame.value = withTiming(
        SPIN_FRAMES,
        { duration: SPIN_MS, easing: Easing.linear },
        (finished) => {
          if (finished) runOnJS(setSpinning)(false)
        },
      )
    }
    onPress()
  }

  return (
    <Touchable onPress={spin} accessibilityLabel={accessibilityLabel}>
      {spinning ? (
        <SpinSprite size={size} frame={frame} ramp={ramp} />
      ) : (
        <LogoIcon size={size} />
      )}
    </Touchable>
  )
}
