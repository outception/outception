import { Box } from '@/components/Shared/Box'
import { GlassSurface } from '@/components/Shared/GlassSurface'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useTheme } from '@/design-system/useTheme'
import {
  dismissActionSheet,
  getActionSheetSnapshot,
  subscribeActionSheet,
} from '@/utils/actionSheet'
import { useEffect, useSyncExternalStore } from 'react'
import { BackHandler, ScrollView, StyleSheet } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

/** The host for {@link showActionSheet}: a bottom-anchored glass card listing
 * every option, for the platform where the native Alert can't (Android caps a
 * dialog at three buttons). Styled like the rest of the wall's glass rather
 * than a system sheet, and mounted once at the root.
 *
 * An in-tree absolute overlay rather than a react-native `Modal`, for the same
 * reason as GlassDialog: on Android a Modal owns its own window and expo-blur
 * can only frost views inside it, so the card would render as a flat grey wash
 * instead of blurring the wall. */
export const ActionSheet = () => {
  const theme = useTheme()
  const insets = useSafeAreaInsets()
  const sheet = useSyncExternalStore(
    subscribeActionSheet,
    getActionSheetSnapshot,
    getActionSheetSnapshot,
  )

  // An overlay gets none of Modal's onRequestClose plumbing, so back has to be
  // wired by hand or it backgrounds the app with the sheet still open.
  useEffect(() => {
    if (sheet === null) return
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      dismissActionSheet()
      return true
    })
    return () => sub.remove()
  }, [sheet])

  if (sheet === null) return null

  // Dismiss FIRST, then act: an option that raises the next sheet (mute word)
  // must not have its sheet torn down by this one's dismissal.
  const choose = (onPress?: () => void) => () => {
    dismissActionSheet()
    onPress?.()
  }

  return (
    <Box style={[StyleSheet.absoluteFill, { zIndex: 50 }]}>
      <Touchable feedback="none" onPress={dismissActionSheet}>
        <Box
          style={[
            StyleSheet.absoluteFill,
            { backgroundColor: theme.colors.scrim, opacity: 0.45 },
          ]}
        />
      </Touchable>
      <Box
        style={{
          position: 'absolute',
          left: 12,
          right: 12,
          bottom: insets.bottom + 12,
          // A long headline plus eight word choices can outgrow a short
          // screen; the list scrolls inside the card rather than running off it.
          maxHeight: '80%',
        }}
      >
        <GlassSurface radius={theme.borderRadii['border-radius-16']} />
        <Box
          borderRadius="border-radius-16"
          overflow="hidden"
          flexDirection="column"
        >
          <Box padding="spacing-16">
            <Text variant="caption" color="subtext">
              {sheet.title}
            </Text>
          </Box>
          <ScrollView>
            {sheet.options.map((option, i) => (
              <Touchable
                key={`${option.label}-${i}`}
                onPress={choose(option.onPress)}
                accessibilityLabel={option.label}
              >
                <Box
                  paddingHorizontal="spacing-16"
                  paddingVertical="spacing-12"
                  borderTopWidth={1}
                  borderColor="borderFaint"
                >
                  <Text color={option.destructive ? 'error' : 'text'}>
                    {option.label}
                  </Text>
                </Box>
              </Touchable>
            ))}
          </ScrollView>
          <Touchable
            onPress={dismissActionSheet}
            accessibilityLabel={sheet.cancel}
          >
            <Box
              paddingHorizontal="spacing-16"
              paddingVertical="spacing-12"
              borderTopWidth={1}
              borderColor="borderStrong"
            >
              <Text color="subtext">{sheet.cancel}</Text>
            </Box>
          </Touchable>
        </Box>
      </Box>
    </Box>
  )
}
