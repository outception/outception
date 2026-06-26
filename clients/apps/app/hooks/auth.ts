import { useOAuthConfig } from '@/hooks/oauth'
import { useSession } from '@/providers/SessionProvider'
import { ExtensionStorage } from '@bacons/apple-targets'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { useQueryClient } from '@tanstack/react-query'
import { revokeAsync } from 'expo-auth-session'
import { useRouter } from 'expo-router'
import * as WebBrowser from 'expo-web-browser'
import { useCallback } from 'react'

const widgetStorage = new ExtensionStorage('group.com.outception.Outception')

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

      widgetStorage.set('widget_api_token', '')
      widgetStorage.set('widget_organization_id', '')
      widgetStorage.set('widget_organization_name', '')

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
