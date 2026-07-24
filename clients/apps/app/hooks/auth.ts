import { useOAuthConfig } from '@/hooks/oauth'
import { useSession } from '@/providers/SessionProvider'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { useQueryClient } from '@tanstack/react-query'
import { revokeAsync, TokenTypeHint } from 'expo-auth-session'
import { useRouter } from 'expo-router'
import * as WebBrowser from 'expo-web-browser'
import { useCallback } from 'react'

export const useLogout = () => {
  const { session, refreshToken, setSession } = useSession()
  const router = useRouter()
  const { CLIENT_ID, discovery } = useOAuthConfig()

  const queryClient = useQueryClient()

  const signOut = useCallback(async () => {
    try {
      // Revoke BOTH tokens server-side, fire-and-forget: the requests start as
      // soon as revokeAsync is called, so we don't await them — otherwise a
      // slow/offline network would make "sign out" hang until the fetch times
      // out. Revoking only the access token would leave the long-lived refresh
      // token able to mint new access tokens after sign-out, so both are killed.
      if (session) {
        revokeAsync(
          {
            token: session,
            tokenTypeHint: TokenTypeHint.AccessToken,
            clientId: CLIENT_ID,
          },
          { revocationEndpoint: discovery.revocationEndpoint },
        ).catch(() => {})
      }
      if (refreshToken) {
        revokeAsync(
          {
            token: refreshToken,
            tokenTypeHint: TokenTypeHint.RefreshToken,
            clientId: CLIENT_ID,
          },
          { revocationEndpoint: discovery.revocationEndpoint },
        ).catch(() => {})
      }

      WebBrowser.coolDownAsync().catch(() => {})
      queryClient.clear()

      // Wipe AsyncStorage-backed preferences (locale override, hidden news
      // sources) so they don't carry over to the next user on a shared device.
      // Tokens live in SecureStore and are cleared by setSession(null) below.
      await AsyncStorage.clear()

      setSession(null)
      router.replace('/')
    } catch (error) {
      console.error('Logout error:', error)
      setSession(null)
      router.replace('/')
    }
  }, [
    session,
    refreshToken,
    setSession,
    router,
    queryClient,
    CLIENT_ID,
    discovery,
  ])

  return signOut
}
