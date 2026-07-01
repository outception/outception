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
  // Let the page (and its fixed SpectraBackground) extend under the iOS status
  // bar / home indicator, so there's no separate band there. Content is kept
  // clear of the notch via env(safe-area-inset-*) padding in the layout.
  viewportFit: 'cover',
  // NOTE: no `themeColor` here on purpose. The site theme is toggled by the
  // logo (next-themes), independent of the OS. An OS-media theme-color would
  // mismatch the toggled theme. Instead a single, site-driven theme-color meta
  // is set at load by the inline script in RootLayout and kept in sync by
  // <ThemeColorMeta />.
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
        {/* Set the browser-bar colour at load to match the *site* theme (which
            the logo toggles), before iOS reads it. <ThemeColorMeta /> keeps it
            in sync afterwards. */}
        <script
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html:
              "(function(){try{var t=localStorage.getItem('theme');var d=t==='dark'||((!t||t==='system')&&window.matchMedia('(prefers-color-scheme: dark)').matches);var m=document.createElement('meta');m.name='theme-color';m.content=d?'#000000':'#fdf4ec';document.head.appendChild(m);}catch(e){}})();",
          }}
        />
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
