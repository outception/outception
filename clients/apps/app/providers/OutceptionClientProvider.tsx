import { refreshMiddleware } from '@/auth/refreshMiddleware'
import { Client, createClient } from '@outception-com/client'
import Constants from 'expo-constants'
import * as Updates from 'expo-updates'
import {
  createContext,
  useContext,
  useMemo,
  type PropsWithChildren,
} from 'react'
import { useSession } from './SessionProvider'

// `version` is the human-readable marketing version, but it relies on a
// developer manually bumping it. `runtimeVersion` (the fingerprint) and
// `updateId` update automatically on every build/OTA, so they're the reliable
// signal for "which exact build is calling this endpoint". `updateId` is null
// on an embedded launch (fresh install before any OTA, or in dev).
const CLIENT_VERSION_HEADERS = {
  'X-outception-Client-Version': `mobile/${Constants.expoConfig?.version ?? 'unknown'}`,
  'X-outception-Client-Runtime': Updates.runtimeVersion ?? 'unknown',
  'X-outception-Client-Update': Updates.updateId ?? 'embedded',
}

const OutceptionClientContext = createContext<{
  outception: Client
}>({
  outception: createClient(
    process.env.EXPO_PUBLIC_OUTCEPTION_SERVER_URL ??
      'https://api.outception.com',
    undefined,
    CLIENT_VERSION_HEADERS,
  ),
})

export function useOutceptionClient() {
  const value = useContext(OutceptionClientContext)
  if (process.env.NODE_ENV !== 'production') {
    if (!value) {
      throw new Error(
        'useOutceptionClient must be wrapped in a <OutceptionClientProvider />',
      )
    }
  }
  return value
}

export function OutceptionClientProvider({ children }: PropsWithChildren) {
  const { session } = useSession()

  const outception = useMemo(() => {
    const client = createClient(
      process.env.EXPO_PUBLIC_OUTCEPTION_SERVER_URL ??
        'https://api.outception.com',
      session ?? '',
      CLIENT_VERSION_HEADERS,
    )
    client.use(refreshMiddleware)
    return client
  }, [session])

  return (
    <OutceptionClientContext.Provider value={{ outception }}>
      {children}
    </OutceptionClientContext.Provider>
  )
}
