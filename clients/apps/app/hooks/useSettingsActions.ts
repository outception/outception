import { useLogout } from '@/hooks/auth'
import { useDeleteUser } from '@/hooks/polar/users'
import { schemas } from '@polar-sh/client'
import { useCallback, useState } from 'react'
import { Alert, Linking } from 'react-native'

const SUPPORT_URL = 'https://polar.sh/docs/support'

interface UseSettingsActionsOptions {
  selectedOrganization: schemas['Organization'] | undefined
  organizations: schemas['Organization'][]
  setOrganization: (organization: schemas['Organization']) => void
  refetch: () => Promise<unknown>
}

export const useSettingsActions = (_options: UseSettingsActionsOptions) => {
  const logout = useLogout()
  const deleteUser = useDeleteUser()

  const [isDeletingAccount, setIsDeletingAccount] = useState(false)

  const showSupportAlert = useCallback((title: string, message: string) => {
    Alert.alert(title, message, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Contact Support',
        onPress: () => Linking.openURL(SUPPORT_URL),
      },
    ])
  }, [])

  const performDeleteAccount = useCallback(async () => {
    setIsDeletingAccount(true)
    try {
      const { data, error } = await deleteUser.mutateAsync()

      if (error) {
        setIsDeletingAccount(false)
        showSupportAlert(
          'Unable to delete account',
          'An unexpected error occurred. Please contact support for assistance.',
        )
        return
      }

      if (data?.deleted) {
        logout()
      } else {
        setIsDeletingAccount(false)
        showSupportAlert(
          'Unable to delete account',
          'Your account could not be deleted. You may need to leave your organizations first. Please contact support for assistance.',
        )
      }
    } catch (err) {
      console.error('[Delete Account] Unexpected error:', err)
      setIsDeletingAccount(false)
      showSupportAlert(
        'Unable to delete account',
        'An unexpected error occurred. Please contact support for assistance.',
      )
    }
  }, [deleteUser, logout, showSupportAlert])

  return {
    performDeleteAccount,
    isDeletingAccount,
    logout,
  }
}
