import { useLogout } from '@/hooks/auth'
import { useDeleteUser } from '@/hooks/outception/users'
import { schemas } from '@outception-com/client'
import { useCallback, useState } from 'react'
import { Alert } from 'react-native'

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

  const showErrorAlert = useCallback((title: string, message: string) => {
    Alert.alert(title, message)
  }, [])

  const performDeleteAccount = useCallback(async () => {
    setIsDeletingAccount(true)
    try {
      const { data, error } = await deleteUser.mutateAsync()

      if (error) {
        setIsDeletingAccount(false)
        showErrorAlert(
          'Unable to delete account',
          'An unexpected error occurred. Please try again.',
        )
        return
      }

      if (data?.deleted) {
        logout()
      } else {
        setIsDeletingAccount(false)
        showErrorAlert(
          'Unable to delete account',
          'Your account could not be deleted. You may need to leave your organizations first.',
        )
      }
    } catch (err) {
      console.error('[Delete Account] Unexpected error:', err)
      setIsDeletingAccount(false)
      showErrorAlert(
        'Unable to delete account',
        'An unexpected error occurred. Please try again.',
      )
    }
  }, [deleteUser, logout, showErrorAlert])

  return {
    performDeleteAccount,
    isDeletingAccount,
    logout,
  }
}
