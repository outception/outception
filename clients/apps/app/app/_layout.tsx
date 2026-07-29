import { PaperTooth } from '@/components/Layout/PaperTooth'
import { SpectraBackground } from '@/components/Layout/SpectraBackground'
import { Box } from '@/components/Shared/Box'
import { editionThemes } from '@/design-system/editionThemes'
import {
  getEditionSnapshot,
  subscribeEdition,
} from '@/design-system/themeStore'
import { LocaleProvider } from '@/providers/LocaleProvider'
import { getLocaleSnapshot } from '@/utils/locale'
import { getTranslations } from '@outception-com/i18n'
import { OutceptionClientProvider } from '@/providers/OutceptionClientProvider'
import { OutceptionQueryClientProvider } from '@/providers/OutceptionQueryClientProvider'
import { SessionProvider } from '@/providers/SessionProvider'
import { warmDeckPositions } from '@/components/News/useSwipeDeck'
import { initializeAds } from '@/utils/ads'
import { Geist_400Regular, Geist_500Medium } from '@expo-google-fonts/geist'
import {
  HankenGrotesk_400Regular,
  HankenGrotesk_500Medium,
  HankenGrotesk_700Bold,
  HankenGrotesk_800ExtraBold,
} from '@expo-google-fonts/hanken-grotesk'
import type { ErrorBoundaryProps } from 'expo-router'
import { Text } from '@/components/Shared/Text'
import { Touchable } from '@/components/Shared/Touchable'
import { useFonts } from 'expo-font'
import NetInfo from '@react-native-community/netinfo'
import * as Sentry from '@sentry/react-native'
import * as Updates from 'expo-updates'

import { ThemeProvider } from '@shopify/restyle'
import { onlineManager } from '@tanstack/react-query'
import { Stack } from 'expo-router'
import * as SplashScreen from 'expo-splash-screen'
import React, { useCallback, useEffect, useSyncExternalStore } from 'react'
import { useTone } from '@/design-system/toneStore'
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
  const [fontsLoaded, fontError] = useFonts({
    Geist_400Regular,
    Geist_500Medium,
    HankenGrotesk_400Regular,
    HankenGrotesk_500Medium,
    HankenGrotesk_700Bold,
    HankenGrotesk_800ExtraBold,
  })

  // Follow the device's system setting (light/dark) for the tone; the active
  // edition (logo-cycled, persisted) picks the palette. Falls back to light.
  const tone = useTone()
  const edition = useSyncExternalStore(
    subscribeEdition,
    getEditionSnapshot,
    getEditionSnapshot,
  )
  const themeSet = editionThemes[edition] ?? editionThemes.phosphor
  const theme = tone === 'dark' ? themeSet.dark : themeSet.light

  // Apply a pending OTA the moment it's fetched instead of waiting for the
  // SECOND cold start: on many Androids "swipe from recents" doesn't kill the
  // process, so the native next-launch apply effectively never runs and users
  // stay pinned to a stale bundle. One quick reload seconds after open is the
  // lesser evil. No-ops in dev and on any failure.
  useEffect(() => {
    const applyPendingUpdate = async () => {
      if (__DEV__) return
      try {
        const check = await Updates.checkForUpdateAsync()
        if (!check.isAvailable) return
        await Updates.fetchUpdateAsync()
        await Updates.reloadAsync()
      } catch {
        // Offline or the update server is unreachable — launch normally.
      }
    }
    void applyPendingUpdate()
  }, [])

  // Consent + ATT + start the Mobile Ads SDK once, off the render path.
  useEffect(() => {
    initializeAds()
    // Pull saved deck positions into memory before the wall mounts, so the deck
    // can seed its first render from them instead of painting card 1 and then
    // jumping to the saved one.
    warmDeckPositions()
  }, [])

  const onLayoutRootView = useCallback(() => {
    if (fontsLoaded || fontError) {
      // This tells the splash screen to hide immediately! If we call this after
      // `setAppIsReady`, then we may see a blank screen while the app is
      // loading its initial state and rendering its first pixels. So instead,
      // we hide the splash screen once we know the root view has already
      // performed layout.
      SplashScreen.hide()
    }
  }, [fontsLoaded, fontError])

  // Render on font error too: otherwise a failed font fetch leaves the splash
  // up forever with no way forward.
  if (!fontsLoaded && !fontError) {
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
                    <Stack
                      screenOptions={{
                        headerShown: false,
                        // Transparent, or native-stack paints its default
                        // light-grey surface over <SpectraBackground /> above.
                        contentStyle: { backgroundColor: 'transparent' },
                      }}
                    />
                    <PaperTooth />
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

/**
 * Root error boundary. expo-router renders this instead of unmounting the tree
 * when a descendant throws — without it any render error (including a failed
 * query, since utils/query.ts sets `throwOnError`) leaves a blank screen with
 * no way back. Deliberately dependency-free: the auth-aware ErrorFallback pulls
 * in login hooks that are disabled in this build.
 */
const CRASH_FALLBACK = { title: 'Something went wrong', retry: 'Try again' }

/** Resolve BOTH strings eagerly inside the guard. Returning a closure that
 * dereferences the translations later would put that access outside the
 * try/catch — and this runs when the tree has already crashed, so a locale
 * missing its `errors` block would make the error boundary itself throw and
 * leave the reader with a blank screen instead of a recovery button. */
const crashStrings = (): { title: string; retry: string } => {
  try {
    const errors = getTranslations(getLocaleSnapshot()).errors
    return {
      title: errors?.crashTitle ?? CRASH_FALLBACK.title,
      retry: errors?.crashRetry ?? CRASH_FALLBACK.retry,
    }
  } catch {
    return CRASH_FALLBACK
  }
}

export function ErrorBoundary({ error, retry }: ErrorBoundaryProps) {
  // Standalone theme: the boundary replaces the whole tree, so it can't read
  // the edition/tone stores through context.
  const theme = editionThemes.phosphor.dark
  // Rendered OUTSIDE LocaleProvider — the provider itself may be what failed —
  // so resolve translations directly from the store rather than via useT, and
  // fall back to English if even that throws.
  const strings = crashStrings()
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <ThemeProvider theme={theme}>
          <Box
            flex={1}
            backgroundColor="background"
            alignItems="center"
            justifyContent="center"
            gap="spacing-16"
            padding="spacing-24"
          >
            <Text variant="title">{strings.title}</Text>
            <Text variant="caption" color="subtext">
              {error.message}
            </Text>
            <Touchable onPress={retry}>
              <Box
                paddingVertical="spacing-12"
                paddingHorizontal="spacing-24"
                borderRadius="border-radius-8"
                backgroundColor="card"
              >
                <Text variant="caption">{strings.retry}</Text>
              </Box>
            </Touchable>
          </Box>
        </ThemeProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  )
}
