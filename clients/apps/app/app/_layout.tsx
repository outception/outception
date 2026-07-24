import { SpectraBackground } from '@/components/Layout/SpectraBackground'
import { Box } from '@/components/Shared/Box'
import { editionThemes } from '@/design-system/editionThemes'
import {
  getEditionSnapshot,
  subscribeEdition,
} from '@/design-system/themeStore'
import { LocaleProvider } from '@/providers/LocaleProvider'
import { OutceptionClientProvider } from '@/providers/OutceptionClientProvider'
import { OutceptionQueryClientProvider } from '@/providers/OutceptionQueryClientProvider'
import { SessionProvider } from '@/providers/SessionProvider'
import { initializeAds } from '@/utils/ads'
import { Geist_400Regular, Geist_500Medium } from '@expo-google-fonts/geist'
import {
  HankenGrotesk_700Bold,
  HankenGrotesk_800ExtraBold,
} from '@expo-google-fonts/hanken-grotesk'
import { useFonts } from 'expo-font'
import NetInfo from '@react-native-community/netinfo'
import * as Sentry from '@sentry/react-native'

import { ThemeProvider } from '@shopify/restyle'
import { onlineManager } from '@tanstack/react-query'
import { Slot } from 'expo-router'
import * as SplashScreen from 'expo-splash-screen'
import React, { useCallback, useEffect, useSyncExternalStore } from 'react'
import { useColorScheme } from 'react-native'
import { GestureHandlerRootView } from 'react-native-gesture-handler'
import { SafeAreaProvider } from 'react-native-safe-area-context'

Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,

  enabled: !__DEV__,

  // Adds more context data to events (IP address, cookies, user, etc.)
  // For more information, visit: https://docs.sentry.io/platforms/react-native/data-management/data-collected/
  sendDefaultPii: true,

  // Enable Logs
  enableLogs: true,

  // Configure Session Replay
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1,
  integrations: [Sentry.mobileReplayIntegration()],

  // Limit breadcrumb size to prevent JSI crashes from oversized payloads
  maxBreadcrumbs: 50,
  beforeBreadcrumb(breadcrumb) {
    if (breadcrumb.data) {
      const serialized = JSON.stringify(breadcrumb.data)
      if (serialized.length > 10_000) {
        breadcrumb.data = { truncated: true, originalLength: serialized.length }
      }
    }
    return breadcrumb
  },

  // uncomment the line below to enable Spotlight (https://spotlightjs.com)
  // spotlight: __DEV__,
})

// Set the animation options. This is optional.
SplashScreen.setOptions({
  duration: 1000,
  fade: true,
})

// Keep the splash screen visible while we fetch resources
SplashScreen.preventAutoHideAsync()

onlineManager.setEventListener((setOnline) => {
  return NetInfo.addEventListener((state) => {
    setOnline(!!state.isConnected)
  })
})

export default Sentry.wrap(function RootLayout() {
  const [fontsLoaded] = useFonts({
    Geist_400Regular,
    Geist_500Medium,
    HankenGrotesk_700Bold,
    HankenGrotesk_800ExtraBold,
  })

  // Follow the device's system setting (light/dark) for the tone; the active
  // edition (logo-cycled, persisted) picks the palette. Falls back to light.
  const scheme = useColorScheme()
  const edition = useSyncExternalStore(
    subscribeEdition,
    getEditionSnapshot,
    getEditionSnapshot,
  )
  const themeSet = editionThemes[edition] ?? editionThemes.phosphor
  const theme = scheme === 'dark' ? themeSet.dark : themeSet.light

  // Consent + ATT + start the Mobile Ads SDK once, off the render path.
  useEffect(() => {
    initializeAds()
  }, [])

  const onLayoutRootView = useCallback(() => {
    if (fontsLoaded) {
      // This tells the splash screen to hide immediately! If we call this after
      // `setAppIsReady`, then we may see a blank screen while the app is
      // loading its initial state and rendering its first pixels. So instead,
      // we hide the splash screen once we know the root view has already
      // performed layout.
      SplashScreen.hide()
    }
  }, [fontsLoaded])

  if (!fontsLoaded) {
    return null
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider theme={theme}>
          <LocaleProvider>
            <SessionProvider>
              <OutceptionClientProvider>
                <OutceptionQueryClientProvider>
                  <Box
                    flex={1}
                    backgroundColor="background"
                    onLayout={onLayoutRootView}
                  >
                    <SpectraBackground />
                    <Slot />
                  </Box>
                </OutceptionQueryClientProvider>
              </OutceptionClientProvider>
            </SessionProvider>
          </LocaleProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
})
