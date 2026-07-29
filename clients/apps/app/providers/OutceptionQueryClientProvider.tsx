import { queryClient } from '@/utils/query'
import { persistOptions } from '@/utils/queryPersist'
import { stopSpeaking } from '@/utils/listen'
import { useReactQueryDevTools } from '@dev-plugins/react-query'
import { focusManager } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import * as Updates from 'expo-updates'
import { useEffect } from 'react'
import { AppState, Platform } from 'react-native'

// Coming back after this long means the reader expects TODAY's wall, not the
// one they left - shorter gaps (article hop, share sheet) keep the gentler
// stale-only focus refetch so the card doesn't reshuffle under them.
const RESUME_REFRESH_GAP_MS = 5 * 60 * 1000
// OTA updates normally only download at cold launch (ON_LOAD), but iOS keeps
// the app alive for days, so a long-lived session never hears about new code.
// Fetching on foreground (throttled) means the next relaunch applies it - one
// relaunch instead of two.
const OTA_CHECK_GAP_MS = 15 * 60 * 1000

// The devtools plugin opens a websocket to the Metro dev server; in a release
// build there is none, so it retries against ws://localhost:8081 forever and
// can throw into the root error boundary. A hook can't be called conditionally,
// so it lives in a component that only renders in development.
function QueryDevTools() {
  useReactQueryDevTools(queryClient)
  return null
}

export function OutceptionQueryClientProvider({
  children,
}: {
  children: React.ReactElement
}) {
  useEffect(() => {
    let backgroundedAt = 0
    let lastOtaCheck = 0
    // TanStack Query cannot see app foregrounding on native by itself;
    // without this, stale queries wait for the next poll tick instead of
    // refetching the moment the user returns.
    const sub = AppState.addEventListener('change', (state) => {
      if (Platform.OS !== 'web') {
        focusManager.setFocused(state === 'active')
      }
      // Don't keep reading headlines aloud once the app leaves the foreground.
      if (state !== 'active') {
        stopSpeaking()
        if (!backgroundedAt) backgroundedAt = Date.now()
        return
      }
      const away = backgroundedAt ? Date.now() - backgroundedAt : 0
      backgroundedAt = 0
      if (away > RESUME_REFRESH_GAP_MS) {
        // The focus refetch alone re-serves whatever the server has cached;
        // invalidating makes the visible card refetch NOW (its query sends
        // latest=true, so the server goes to the publisher) - the same
        // refresh a swipe-away-and-back triggered, without the swipe.
        void queryClient.invalidateQueries()
      }
      if (
        !__DEV__ &&
        Updates.isEnabled &&
        Date.now() - lastOtaCheck > OTA_CHECK_GAP_MS
      ) {
        lastOtaCheck = Date.now()
        void Updates.checkForUpdateAsync()
          .then((found) =>
            found.isAvailable ? Updates.fetchUpdateAsync() : null,
          )
          .catch(() => undefined)
      }
    })
    return () => sub.remove()
  }, [])

  // PersistQueryClientProvider restores the cached wall from AsyncStorage on
  // launch (children render immediately; refetching resumes once restored), so
  // the last-loaded deck and headlines are readable offline.
  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={persistOptions}
    >
      {__DEV__ ? <QueryDevTools /> : null}
      {children}
    </PersistQueryClientProvider>
  )
}
