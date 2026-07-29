import { Box } from '@/components/Shared/Box'
import { useTone } from '@/design-system/toneStore'
import { Image, StyleSheet } from 'react-native'

/** A fine full-bleed noise tooth laid OVER the whole wall (below modals),
 * mirroring the web's `body::after` fractal-noise sheet — so cards read as
 * printed on aged stock, not just the backdrop. Balanced speckle (net-neutral
 * luminance) at low opacity so text stays crisp; RN has no `mix-blend-mode`, so
 * the neutrality is what keeps it from casting a tint. */
export const PaperTooth = () => {
  const tone = useTone()
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
