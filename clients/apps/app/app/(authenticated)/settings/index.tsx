import { PromotionEmailToggle } from '@/components/Settings/PromotionEmailToggle'
import { SettingsItem } from '@/components/Settings/SettingsList'
import { Box } from '@/components/Shared/Box'
import { Text } from '@/components/Shared/Text'
import { useTheme } from '@/design-system/useTheme'
import { useSettingsActions } from '@/hooks/useSettingsActions'
import Constants from 'expo-constants'
import { useUpdates } from 'expo-updates'
import { Stack } from 'expo-router'
import React from 'react'
import { Alert, ScrollView } from 'react-native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

const APP_VERSION = Constants.expoConfig?.version ?? 'Unknown'

function UpdateId() {
  const { currentlyRunning } = useUpdates()
  const updateId = currentlyRunning.updateId

  if (!updateId) return null

  return (
    <Text variant="caption" color="subtext" textAlign="center">
      {updateId.slice(0, 8)}
    </Text>
  )
}

export default function Index() {
  const theme = useTheme()
  const { logout, performDeleteAccount } = useSettingsActions()
  const safeAreaInsets = useSafeAreaInsets()

  const confirmDeleteAccount = () =>
    Alert.alert(
      'Delete account',
      'This permanently deletes your account. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            void performDeleteAccount()
          },
        },
      ],
    )

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ScrollView
        contentContainerStyle={{
          flex: 1,
          margin: theme.spacing['spacing-16'],
          gap: theme.spacing['spacing-24'],
          justifyContent: 'space-between',
          paddingBottom: safeAreaInsets.bottom,
        }}
      >
        <Stack.Screen options={{ title: 'Settings' }} />
        <Box>
          <PromotionEmailToggle />
          <Box height={1} backgroundColor="border" marginVertical="spacing-8" />
          <SettingsItem
            title="Delete Account"
            variant="navigate"
            onPress={confirmDeleteAccount}
          />
          <SettingsItem title="Logout" variant="navigate" onPress={logout} />
        </Box>
        <Box
          justifyContent="center"
          flexDirection="column"
          alignItems="center"
          gap="spacing-4"
        >
          <Text variant="body" color="subtext" textAlign="center">
            {`Outception (${APP_VERSION})`}
          </Text>
          <UpdateId />
        </Box>
      </ScrollView>
    </GestureHandlerRootView>
  )
}
