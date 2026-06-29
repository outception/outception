import { useOAuthConfig } from '@/hooks/oauth'
import { useSession } from '@/providers/SessionProvider'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { useQueryClient } from '@tanstack/react-query'
import { revokeAsync } from 'expo-auth-session'
import { useRouter } from 'expo-router'
import * as WebBrowser from 'expo-web-browser'
import { useCallback } from 'react'

export const useLogout = () => {
  const { session, setSession } = useSession()
  const router = useRouter()
  const { CLIENT_ID, discovery } = useOAuthConfig()

  const queryClient = useQueryClient()

  const signOut = useCallback(async () => {
    try {
      if (session) {
        revokeAsync(
          { token: session, clientId: CLIENT_ID },
          { revocationEndpoint: discovery.revocationEndpoint },
        ).catch(() => {})
      }

      WebBrowser.coolDownAsync().catch(() => {})
      queryClient.clear()
      await AsyncStorage.clear()

      setSession(null)
      router.replace('/')
    } catch (error) {
      console.error('Logout error:', error)
      setSession(null)
      router.replace('/')
    }
  }, [session, setSession, router, queryClient, CLIENT_ID, discovery])

  return signOut
}
