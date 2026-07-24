import { api } from '@/utils/client'
import { schemas, unwrap } from '@outception-com/client'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo } from 'react'
import { useAuth } from '.'

export const useOAuthAccounts = (): schemas['OAuthAccountRead'][] => {
  const { currentUser } = useAuth()
  return currentUser?.oauth_accounts || []
}

const usePlatformOAuthAccount = (
  platform: schemas['OAuthPlatform'],
): schemas['OAuthAccountRead'] | undefined => {
  const oauthAccounts = useOAuthAccounts()
  return useMemo(
    () =>
      oauthAccounts.find((oauthAccount) => oauthAccount.platform === platform),
    [oauthAccounts, platform],
  )
}

export const useMicrosoftAccount = ():
  | schemas['OAuthAccountRead']
  | undefined => usePlatformOAuthAccount('microsoft')

export const useGoogleAccount = (): schemas['OAuthAccountRead'] | undefined =>
  usePlatformOAuthAccount('google')

export const useDisconnectOAuthAccount = () => {
  const queryClient = useQueryClient()
  const { reloadUser } = useAuth()

  return useMutation({
    mutationFn: (platform: schemas['OAuthPlatform']) =>
      // unwrap throws on error responses (e.g. 400 "can't disconnect your last
      // login method") so onSuccess can't fire on a failed disconnect and the
      // caller's onError surfaces the reason.
      unwrap(
        api.DELETE('/v1/users/me/oauth-accounts/{platform}', {
          params: { path: { platform } },
        }),
      ),
    onSuccess: async () => {
      // Reload user data to get updated oauth_accounts list
      await reloadUser()
      // Invalidate queries that might depend on OAuth accounts
      queryClient.invalidateQueries({ queryKey: ['user'] })
    },
  })
}
