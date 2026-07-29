import { useTone } from '@/design-system/toneStore'
import { useTheme } from '@/design-system/useTheme'
import { BlurView } from 'expo-blur'
import type { PropsWithChildren } from 'react'
import { StyleSheet, View } from 'react-native'

/**
 * The frosted sheet used by dialogs, mirroring the web's `.paper-search`.
 *
 * Web applies glassmorphism ONLY to dialog surfaces — the search, language,
 * privacy and terms panels — not to the wall, the cards or the header. This is
 * the native equivalent: `expo-blur` for the backdrop blur, plus a translucent
 * wash and a hairline inset ring over it.
 *
 * Web values this mirrors (globals.css `.paper-search`):
 *   backdrop-filter: blur(28px) saturate(180%)
 *   light — paper-sheet at 72% opacity, inset ring ink at 14%
 *   dark  — paper-night-raised at 60% opacity, inset ring ink-night at 20%
 *
 * `saturate(180%)` has no expo-blur equivalent, so the wash carries slightly
 * more of the surface colour to compensate.
 *
 * Uses raw `View` rather than `Box`: these are absolutely-positioned
 * compositing layers with no design-system semantics — same exemption
 * SpectraBackground and PaperTooth take for the grain overlay.
 */
/* eslint-disable @outception/no-view */
export const GlassSurface = ({
  children,
  radius = 0,
  style,
}: PropsWithChildren<{
  radius?: number
  style?: object
}>) => {
  const theme = useTheme()
  const tone = useTone()

  return (
    // absoluteFillObject FIRST so a caller's `style` can still reposition or
    // resize the surface; last, it silently overrode every one of those props.
    <View
      style={[
        StyleSheet.absoluteFillObject,
        { borderRadius: radius, overflow: 'hidden' },
        style,
      ]}
      // Only the decorative layers ignore touches — children must stay
      // interactive, or anything placed inside is silently inert.
      pointerEvents="box-none"
    >
      <BlurView
        // Softer than the CSS blur(28px) equivalent: expo-blur's tint layers
        // its own wash on top of ours, so at 80 the pane read fully opaque —
        // 55 keeps the wall's shapes ghosting through like the web.
        intensity={55}
        tint={tone === 'dark' ? 'dark' : 'light'}
        // Android defaults to 'none', which silently degrades to a plain
        // translucent view — no blur at all. This opts into the real
        // implementation; it can only blur views within its own window, which
        // is why the sheet is an in-tree overlay rather than a Modal.
        experimentalBlurMethod="dimezisBlurView"
        style={StyleSheet.absoluteFill}
        pointerEvents="none"
      />
      <View
        pointerEvents="none"
        style={[
          StyleSheet.absoluteFill,
          {
            backgroundColor: theme.colors.card,
            // Well below the web's 60/72%: the BlurView tint already whitens/
            // darkens the pane, so the same wash values read opaque on device.
            // These land at the web's PERCEIVED translucency — content behind
            // ghosts through, text on the pane stays legible.
            opacity: tone === 'dark' ? 0.45 : 0.5,
          },
        ]}
      />
      <View
        pointerEvents="none"
        style={[
          StyleSheet.absoluteFill,
          {
            borderRadius: radius,
            borderWidth: StyleSheet.hairlineWidth,
            borderColor: theme.colors.border,
            opacity: tone === 'dark' ? 0.2 : 0.14,
          },
        ]}
      />
      {children}
    </View>
  )
}
