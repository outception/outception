'use client'

import { ThemeColorMeta } from '@/components/ThemeColorMeta'
import { getQueryClient } from '@/utils/api/query'
import { QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import { usePathname, useSearchParams } from 'next/navigation'
import { NuqsAdapter } from 'nuqs/adapters/next/app'
import { PropsWithChildren } from 'react'

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
  nonce,
}: {
  children: React.ReactNode
  forceTheme?: 'light' | 'dark'
  /** The request's script nonce: the provider injects an inline script
   * of its own, which the policy only runs when it carries it. */
  nonce?: string
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
      nonce={nonce}
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
