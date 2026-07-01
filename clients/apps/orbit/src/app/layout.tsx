import '../styles/globals.css'

import type { Metadata, Viewport } from 'next'
import { AppShell } from '@/components/AppShell'
import { OrbitThemeProvider } from './providers'

export const metadata: Metadata = {
  title: 'Orbit — Outception Design System',
  description:
    'Playground and documentation for Orbit, the Outception design system: components, variants, usage and design tokens.',
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning className="antialiased">
      <body>
        <OrbitThemeProvider>
          <AppShell>{children}</AppShell>
        </OrbitThemeProvider>
      </body>
    </html>
  )
}
