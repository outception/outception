import { useOAuthConfig } from '@/hooks/oauth'
import { useSession } from '@/providers/SessionProvider'
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
      // soon as revokeAsync is called, so we don't await them - otherwise a
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

      // Nothing account-scoped lives in AsyncStorage - it holds only reader
      // preferences (language, theme edition, tone, deck position, hidden and
      // followed sources), and tokens live in SecureStore, cleared by
      // setSession(null) below. The old `AsyncStorage.clear()` here wiped all
      // of those; worse, the error boundary offers this same action after a
      // network failure, so one offline blip erased every preference.

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
