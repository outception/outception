import '../styles/globals.css'

import { getExperimentNames } from '@/experiments'
import { getDistinctId } from '@/experiments/distinct-id'
import { ExperimentProvider } from '@/experiments/ExperimentProvider'
import { getExperiments } from '@/experiments/server'
import { UserContextProvider } from '@/providers/auth'
import { LocaleProvider } from '@/providers/locale'
import { resolveLocale } from '@/utils/i18n'
import { getAuthenticatedUser, getUserOrganizations } from '@/utils/user'
import { schemas } from '@outception-com/client'
import { PHASE_PRODUCTION_BUILD } from 'next/constants'
import { Viewport } from 'next/types'
import {
  NavigationHistoryProvider,
  OutceptionNuqsProvider,
  OutceptionPostHogProvider,
  OutceptionQueryClientProvider,
} from './providers'

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // Tint the mobile browser chrome (iOS status bar, Safari toolbar) to match
  // the page's base colour so the top/bottom don't read as a separate band.
  // Values mirror the `body` background in globals.css.
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#e9dcbf' },
    { media: '(prefers-color-scheme: dark)', color: '#211a12' },
  ],
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  let authenticatedUser: schemas['UserRead'] | undefined = undefined
  let userOrganizations: schemas['OrganizationWithRole'][] = []

  try {
    authenticatedUser = await getAuthenticatedUser()
    userOrganizations = await getUserOrganizations()
  } catch (e) {
    if (process.env.NEXT_PHASE !== PHASE_PRODUCTION_BUILD) {
      throw e
    }
  }

  const distinctId = await getDistinctId()
  const experimentVariants = await getExperiments(getExperimentNames(), {
    distinctId,
  })
  const locale = await resolveLocale()

  return (
    <html lang="en" suppressHydrationWarning className="antialiased">
      <body style={{ textRendering: 'optimizeLegibility' }}>
        <ExperimentProvider experiments={experimentVariants}>
          <UserContextProvider
            user={authenticatedUser}
            userOrganizations={userOrganizations}
          >
            <OutceptionPostHogProvider>
              <OutceptionQueryClientProvider>
                <OutceptionNuqsProvider>
                  <NavigationHistoryProvider>
                    <LocaleProvider locale={locale}>{children}</LocaleProvider>
                  </NavigationHistoryProvider>
                </OutceptionNuqsProvider>
              </OutceptionQueryClientProvider>
            </OutceptionPostHogProvider>
          </UserContextProvider>
        </ExperimentProvider>
      </body>
    </html>
  )
}
