import { useLogout } from '@/hooks/auth'
import { useDeleteUser } from '@/hooks/outception/users'
import { useCallback, useState } from 'react'
import { Alert } from 'react-native'

export const useSettingsActions = () => {
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
          'Your account could not be deleted. Please try again.',
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
