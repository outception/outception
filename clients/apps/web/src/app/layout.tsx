import '../styles/globals.css'

import { getExperimentNames } from '@/experiments'
import { getDistinctId } from '@/experiments/distinct-id'
import { ExperimentProvider } from '@/experiments/ExperimentProvider'
import { getExperiments } from '@/experiments/server'
import { UserContextProvider } from '@/providers/auth'
import { LocaleProvider } from '@/providers/locale'
import { CONFIG } from '@/utils/config'
import { resolveLocale } from '@/utils/i18n'
import { getAuthenticatedUser, getUserOrganizations } from '@/utils/user'
import { schemas } from '@outception-com/client'
import { getLocaleDir } from '@outception-com/i18n'
import { Metadata, Viewport } from 'next/types'
import { ConsentedGoogleAnalytics } from '@/components/Analytics/ConsentedGoogleAnalytics'
import { GoogleConsentDefaults } from '@/components/Analytics/GoogleConsentDefaults'
import {
  NavigationHistoryProvider,
  OutceptionNuqsProvider,
  OutceptionPostHogProvider,
  OutceptionQueryClientProvider,
} from './providers'

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  // Let the page (and its fixed PaperBackground) extend under the iOS status
  // bar / home indicator, so there's no separate band there. Content is kept
  // clear of the notch via env(safe-area-inset-*) padding in the layout.
  viewportFit: 'cover',
  // No `themeColor`: the site theme is toggled by the logo (next-themes),
  // independent of the OS, so an OS-media theme-color would mismatch it. In a
  // browser tab the system status bar can't show page content anyway; in a
  // Home-Screen install the black-translucent status bar (below) handles it.
}

export const metadata: Metadata = {
  // Base for resolving relative URLs (notably the file-based opengraph-image /
  // twitter-image) to absolute ones, so social crawlers get a fully-qualified
  // og:image and render the preview card.
  metadataBase: new URL(CONFIG.FRONTEND_BASE_URL),
  // When added to the iOS Home Screen the site runs standalone with a
  // TRANSLUCENT status bar, so the fixed PaperBackground draws
  // edge-to-edge under the clock/battery. A normal Safari browser tab can't do
  // this — the top status bar is system chrome there.
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Outception',
  },
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
  } catch {
    // API unreachable — most commonly the few-second window where a rolling
    // deploy restarts web before the API is Ready (ECONNREFUSED on the SSR
    // fetch). Render anonymously instead of error-paging the whole wall: the
    // wall is public and accounts are disabled, so nothing is lost.
  }

  const distinctId = await getDistinctId()
  const experimentVariants = await getExperiments(getExperimentNames(), {
    distinctId,
  })
  const locale = await resolveLocale()

  return (
    <html
      lang={locale}
      dir={getLocaleDir(locale)}
      suppressHydrationWarning
      className="antialiased"
    >
      <body style={{ textRendering: 'optimizeLegibility' }}>
        {/* Resolve the wall edition before first paint: the stored choice
            (with legacy-id migration), else the default edition Ruby
            (mirrors wallTheme.ts DEFAULT_WALL_THEME_ID). The tone follows the
            OS, picking the edition's light or dark chrome to tint the
            browser-tab status bar / Android address bar; kept in sync
            afterwards by <ThemeColorMeta />. A Home-Screen install ignores
            this in favour of the black-translucent status bar, so
            edge-to-edge is unaffected. The chrome map and the 'ruby'
            default are duplicated from WALL_THEMES / DEFAULT_WALL_THEME_ID
            because this runs before any module loads — brand.test.ts guards
            both against drift. */}
        <script
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var c={midnight:['#e9eef4','#101413'],tide:['#dceefa','#063d61'],neon:['#fae4f0','#25101f'],dune:['#f2ddc0','#1d1410'],phosphor:['#dff4e7','#020403'],ruby:['#f0eee6','#1a0407']};var g={daybreak:'dune',light:'dune',technical:'dune','studio-showroom':'dune',beach:'dune',dark:'midnight',blue:'tide',pink:'neon','clay-sunrise':'dune',terminal:'phosphor'};var t=localStorage.getItem('theme');var d=t==='dark'||((!t||t==='system')&&window.matchMedia('(prefers-color-scheme: dark)').matches);var w=localStorage.getItem('news.wallTheme');var id=w?(g[w]||w):'ruby';if(!c[id]){id='ruby';}document.documentElement.dataset.theme=id;if(d){document.documentElement.classList.add('dark');}var m=document.createElement('meta');m.name='theme-color';m.content=c[id][d?1:0];document.head.appendChild(m);}catch(e){}})();`,
          }}
        />
        {/* Consent Mode v2 defaults — must precede every Google tag below. */}
        <GoogleConsentDefaults />
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
        {/* Google Analytics under Consent Mode v2: cookieless until the reader
            accepts (mirroring PostHog's memory mode), full measurement after. */}
        <ConsentedGoogleAnalytics />
      </body>
    </html>
  )
}
