import { queryClient } from '@/utils/query'
import { persistOptions } from '@/utils/queryPersist'
import { stopSpeaking } from '@/utils/listen'
import { useReactQueryDevTools } from '@dev-plugins/react-query'
import { focusManager } from '@tanstack/react-query'
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client'
import { useEffect } from 'react'
import { AppState, Platform } from 'react-native'

export function OutceptionQueryClientProvider({
  children,
}: {
  children: React.ReactElement
}) {
  useReactQueryDevTools(queryClient)

  useEffect(() => {
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
      {children}
    </PersistQueryClientProvider>
  )
}
