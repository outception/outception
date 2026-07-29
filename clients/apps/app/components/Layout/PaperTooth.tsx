import { Box } from '@/components/Shared/Box'
import { useTone } from '@/design-system/toneStore'
import { Image, Platform, StyleSheet } from 'react-native'

/** A fine full-bleed noise tooth laid OVER the whole wall (below modals),
 * mirroring the web's `body::after` fractal-noise sheet — so cards read as
 * printed on aged stock, not just the backdrop. Balanced speckle (net-neutral
 * luminance) at low opacity so text stays crisp; RN has no `mix-blend-mode`, so
 * the neutrality is what keeps it from casting a tint. */
export const PaperTooth = () => {
  const tone = useTone()
  // iOS only. On new-arch Android `resizeMode="repeat"` silently paints the
  // 128px tile ONCE (see SpectraBackground's grain notes), so this layer was
  // one faint square plus a permanent full-screen composite over every frame
  // of every swipe and scroll — all cost, no tooth.
  if (Platform.OS !== 'ios') return null
  return (
    <Box
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        { opacity: tone === 'dark' ? 0.1 : 0.06 },
      ]}
    >
      {/* eslint-disable-next-line @outception/no-image */}
      <Image
        source={require('../../assets/images/tooth.png')}
        resizeMode="repeat"
        style={StyleSheet.absoluteFill}
        fadeDuration={0}
      />
    </Box>
  )
}
