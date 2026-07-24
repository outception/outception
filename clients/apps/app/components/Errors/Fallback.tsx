import { useMemo } from 'react'

import { Box } from '@/components/Shared/Box'
import OutceptionLogo from '@/components/Shared/OutceptionLogo'
import { useTheme } from '@/design-system/useTheme'
import { useLogout } from '@/hooks/auth'
import { useOAuth } from '@/hooks/oauth'
import { useT } from '@/providers/LocaleProvider'
import {
  isValidationError,
  UnauthorizedResponseError,
} from '@outception-com/client'
import { Text } from '../Shared/Text'
import { Touchable } from '../Shared/Touchable'
export interface ErrorFallbackProps {
  error: Error
  resetErrorBoundary: () => void
}

export const ErrorFallback = ({
  error,
  resetErrorBoundary,
}: ErrorFallbackProps) => {
  const theme = useTheme()
  const t = useT()
  const logout = useLogout()
  const { authenticate } = useOAuth()
  const permissionError =
    error instanceof UnauthorizedResponseError ||
    (isValidationError(error) &&
      error.message.includes('insufficient_scope')) ||
    (error instanceof Error && error.message.includes('privileges'))

  const title = permissionError
    ? t('errors.permissionTitle')
    : t('errors.genericTitle')

  const message = permissionError
    ? t('errors.permissionMessage')
    : t('errors.genericMessage')

  const [actionText, action] = useMemo(
    () =>
      permissionError
        ? ([t('errors.authenticate'), authenticate] as const)
        : ([t('errors.logout'), logout] as const),
    [permissionError, logout, authenticate, t],
  )

  return (
    <Box
      flex={1}
      justifyContent="center"
      alignItems="center"
      backgroundColor="background"
      gap="spacing-32"
      paddingHorizontal="spacing-24"
    >
      <OutceptionLogo size={80} />
      <Box gap="spacing-12">
        <Text variant="titleLarge" textAlign="center">
          {title}
        </Text>
        <Text color="subtext" textAlign="center">
          {message}
        </Text>
      </Box>
      <Touchable
        activeOpacity={0.6}
        style={{
          backgroundColor: theme.colors.monochromeInverted,
          borderRadius: 100,
          width: 'auto',
          paddingVertical: theme.spacing['spacing-12'],
          paddingHorizontal: theme.spacing['spacing-24'],
        }}
        onPress={async () => {
          await action()
          resetErrorBoundary()
        }}
      >
        <Text variant="bodyMedium" style={{ color: theme.colors.monochrome }}>
          {actionText}
        </Text>
      </Touchable>
    </Box>
  )
}
