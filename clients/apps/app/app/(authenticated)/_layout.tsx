import { ErrorFallback } from '@/components/Errors/Fallback'
import { useTheme } from '@/design-system/useTheme'
import { useAppOpenTracking } from '@/hooks/useAppOpenTracking'
import DeepLinkProvider from '@/providers/DeepLinkProvider'
import { useSession } from '@/providers/SessionProvider'
import { ToastProvider } from '@/providers/ToastProvider'
import { UserProvider } from '@/providers/UserProvider'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import {
  DarkTheme,
  DefaultTheme,
  ThemeProvider,
} from '@react-navigation/native'
import { useQueryClient } from '@tanstack/react-query'
import { Redirect, Stack, useRouter } from 'expo-router'
import { PropsWithChildren } from 'react'
import { ErrorBoundary as ErrorBoundaryComponent } from 'react-error-boundary'
import { StatusBar, useColorScheme } from 'react-native'

const AuthenticatedErrorBoundary = ({ children }: PropsWithChildren) => {
  const queryClient = useQueryClient()
  const router = useRouter()

  return (
    <ErrorBoundaryComponent
      onReset={() => {
        queryClient.clear()
        router.replace('/')
      }}
      fallbackRender={({ error, resetErrorBoundary }) => (
        <ErrorFallback error={error} resetErrorBoundary={resetErrorBoundary} />
      )}
    >
      {children}
    </ErrorBoundaryComponent>
  )
}

const RootLayout = () => {
  const theme = useTheme()
  const { session } = useSession()
  const scheme = useColorScheme()

  useAppOpenTracking()

  if (!ACCOUNTS_ENABLED || !session) {
    return <Redirect href="/" />
  }

  return (
    <>
      <StatusBar
        barStyle={scheme === 'dark' ? 'light-content' : 'dark-content'}
      />
      <Stack
        screenOptions={{
          headerStyle: {
            backgroundColor: theme.colors.background,
          },
          headerTitleStyle: {
            color: theme.colors.text,
            fontSize: 18,
          },
          contentStyle: { backgroundColor: theme.colors.background },
          headerShadowVisible: false,
        }}
      />
    </>
  )
}

export default function Providers() {
  const scheme = useColorScheme()
  return (
    <ThemeProvider value={scheme === 'dark' ? DarkTheme : DefaultTheme}>
      <DeepLinkProvider>
        <AuthenticatedErrorBoundary>
          <UserProvider>
            <ToastProvider>
              <RootLayout />
            </ToastProvider>
          </UserProvider>
        </AuthenticatedErrorBoundary>
      </DeepLinkProvider>
    </ThemeProvider>
  )
}
