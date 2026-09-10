'use client'

import {
  cookieConsentGiven,
  writeCookieConsent,
} from '@/components/Privacy/CookieConsent'
import { ThemeColorMeta } from '@/components/ThemeColorMeta'
import { DISTINCT_ID_COOKIE } from '@/experiments/constants'
import { NavigationHistoryProvider } from '@/providers/navigationHistory'
import { getQueryClient } from '@/utils/api/query'
import { CONFIG } from '@/utils/config'
import { QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import { usePathname, useSearchParams } from 'next/navigation'
import { NuqsAdapter } from 'nuqs/adapters/next/app'
import { runWhenIdle } from '@/utils/idle'
import posthog from 'posthog-js'
import { PostHogProvider } from 'posthog-js/react'
import { PropsWithChildren, useEffect } from 'react'

export { NavigationHistoryProvider }

// Deferred to idle (see OutceptionPostHogProvider): initializing at module
// scope put PostHog's parse and first network calls inside the wall's
// critical first paint. Init still auto-captures the pageview when it runs.
const initPostHog = () => {
  if (!CONFIG.POSTHOG_TOKEN || posthog.__loaded) return
  const consent = cookieConsentGiven()
  const consented = consent === 'yes'
  // Readers who decided before the cookie mirror existed only have the
  // localStorage value; re-mirror it so the proxy can act on it.
  if (consent === 'yes' || consent === 'no') writeCookieConsent(consent)
  // Without consent there is no persistent id at all: memory persistence and
  // no bootstrap, so nothing ties this session to a previous one.
  const distinctId = consented
    ? document.cookie
        .split('; ')
        .find((row) => row.startsWith(`${DISTINCT_ID_COOKIE}=`))
        ?.split('=')[1]
    : undefined

  posthog.init(CONFIG.POSTHOG_TOKEN, {
    ui_host: 'https://eu.i.posthog.com',
    api_host: '/ingest',
    defaults: '2025-05-24', // enables automatic pageview tracking
    persistence: consented ? 'localStorage' : 'memory',
    bootstrap: distinctId ? { distinctID: distinctId } : undefined,
    disable_surveys: true,
  })
}

export function OutceptionPostHogProvider({
  children,
}: {
  children: React.ReactNode
}) {
  useEffect(() => runWhenIdle(initPostHog), [])
  return <PostHogProvider client={posthog}>{children}</PostHogProvider>
}

const FORCED_DARK_PREFIXES = ['/legal']

// Note: the home page ('/') is intentionally NOT forced - the landing logo
// toggles light/dark, and that choice must persist across every page.
const isForcedDarkPath = (pathname: string): boolean =>
  FORCED_DARK_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  )

export function OutceptionThemeProvider({
  children,
  forceTheme,
}: {
  children: React.ReactNode
  forceTheme?: 'light' | 'dark'
}) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const theme = searchParams.get('theme')

  const forcedTheme = isForcedDarkPath(pathname) ? 'dark' : forceTheme

  return (
    <ThemeProvider
      defaultTheme="system"
      enableSystem
      attribute="class"
      forcedTheme={theme ?? forcedTheme}
    >
      <ThemeColorMeta />
      {children}
    </ThemeProvider>
  )
}

export function OutceptionQueryClientProvider({
  children,
}: {
  children: React.ReactNode
}) {
  const queryClient = getQueryClient()

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

export function OutceptionNuqsProvider({ children }: PropsWithChildren) {
  return <NuqsAdapter>{children}</NuqsAdapter>
}
