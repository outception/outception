'use client'

import { useTheme } from 'next-themes'
import { useEffect } from 'react'

// The site theme is toggled by the logo (next-themes), independent of the OS,
// so an OS-media <meta theme-color> would mismatch it. This keeps a single
// theme-color meta in sync with the *resolved site theme* — it tints the
// browser-tab status bar and Android Chrome's address bar to match the page.
// (A Home-Screen install uses the black-translucent status bar instead, so this
// doesn't affect the edge-to-edge look there.)
const THEME_COLORS = { light: '#fdf4ec', dark: '#000000' } as const

export const ThemeColorMeta = () => {
  const { resolvedTheme } = useTheme()

  useEffect(() => {
    const color =
      resolvedTheme === 'dark' ? THEME_COLORS.dark : THEME_COLORS.light
    let meta = document.querySelector<HTMLMetaElement>(
      'meta[name="theme-color"]',
    )
    if (!meta) {
      meta = document.createElement('meta')
      meta.name = 'theme-color'
      document.head.appendChild(meta)
    }
    meta.content = color
  }, [resolvedTheme])

  return null
}

export default ThemeColorMeta
