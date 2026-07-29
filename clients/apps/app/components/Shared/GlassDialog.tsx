import { Box } from '@/components/Shared/Box'
import { GlassSurface } from '@/components/Shared/GlassSurface'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import type { PropsWithChildren } from 'react'
import { useEffect } from 'react'
import { BackHandler, StyleSheet } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'

/**
 * A frosted modal card floating over the wall — the native twin of the web's
 * `<Dialog>` + `.paper-search` surface (search, language, legal panels): the
 * wall stays visible around the card, the card blurs what's behind it, and
 * tapping anywhere outside the card dismisses it.
 *
 * An in-tree absolute overlay rather than a react-native `Modal`: on Android a
 * Modal is a Dialog in its OWN window, and expo-blur can only blur views inside
 * its own window — behind a Modal the frost would capture nothing and render as
 * a flat grey wash. As an overlay it sits in the same hierarchy as the wall and
 * actually blurs it.
 *
 * The backdrop is a sibling BELOW the card layer: taps that nothing in the card
 * subtree claims fall through the `box-none` wrappers and land on it, closing
 * the dialog — taps inside the card never reach it.
 */
export const GlassDialog = ({
  visible,
  onClose,
  children,
}: PropsWithChildren<{
  visible: boolean
  onClose: () => void
}>) => {
  const theme = useTheme()

  // An in-tree overlay gets none of Modal's onRequestClose plumbing, so the
  // Android back button/gesture must be wired by hand — otherwise it
  // backgrounds the app with the dialog still open.
  useEffect(() => {
    if (!visible) return
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      onClose()
      return true
    })
    return () => sub.remove()
  }, [visible, onClose])

  if (!visible) return null

  return (
    <Box style={[StyleSheet.absoluteFill, { zIndex: 40 }]}>
      {/* Scrim: the web's `.paper-overlay` — a 45% ink dim (no blur) so the
          open palette clearly reads as the focus while the wall stays legible. */}
      <Touchable feedback="none" onPress={onClose}>
        <Box
          style={[
            StyleSheet.absoluteFill,
            { backgroundColor: theme.colors.text, opacity: 0.45 },
          ]}
        />
      </Touchable>
      <SafeAreaView
        style={{ flex: 1 }}
        edges={['top', 'bottom']}
        pointerEvents="box-none"
      >
        {/* Insets mirror the web dialog's footprint: nearly full width, the
            nav pill peeking above, a strip of wall below (max-h-[85dvh]). */}
        <Box
          flex={1}
          pointerEvents="box-none"
          paddingHorizontal="spacing-12"
          paddingTop="spacing-56"
          paddingBottom="spacing-48"
        >
          {/* Dialog-scale drop shadow (web: 0 28px 64px) — iOS only. Android
              elevation needs an opaque background, which would sit behind the
              glass and kill its translucency; there the scrim carries the
              depth instead. shadowColor left unset (RN defaults to black),
              matching the card components' no-hardcoded-colors approach.
              The glass has no opaque background, so Core Animation derives
              this shadow from the rendered alpha — an offscreen pass that
              re-runs while the roster scrolls. Keep the kernel small: 16
              reads near-identical over the 45% scrim at half the blur cost. */}
          <Box
            flex={1}
            borderRadius="border-radius-16"
            style={{
              shadowOpacity: 0.3,
              shadowRadius: 16,
              shadowOffset: {
                width: 0,
                height: theme.dimension['dimension-16'],
              },
            }}
          >
            <Box
              flex={1}
              borderRadius="border-radius-16"
              overflow="hidden"
              flexDirection="column"
            >
              <GlassSurface radius={theme.borderRadii['border-radius-16']} />
              {children}
            </Box>
          </Box>
        </Box>
      </SafeAreaView>
    </Box>
  )
}
