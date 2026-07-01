'use client'

import { useTheme } from 'next-themes'
import { useEffect } from 'react'

// The site theme is controlled by next-themes (a .dark class toggled by the
// logo), which is independent of the OS `prefers-color-scheme`. A media-query
// <meta theme-color> would therefore mismatch whenever the user toggles the
// site theme against their OS setting (dark site on a light phone → light
// browser chrome on a dark page = the "band"). This keeps the browser chrome
// colour in sync with the *resolved site theme* instead.
const THEME_COLORS = { light: '#fdf4ec', dark: '#000000' } as const

export const ThemeColorMeta = () => {
  const { resolvedTheme } = useTheme()

  useEffect(() => {
    const color =
      resolvedTheme === 'dark' ? THEME_COLORS.dark : THEME_COLORS.light
    // Drop any OS-media-scoped theme-color metas so ours is authoritative.
    document
      .querySelectorAll('meta[name="theme-color"][media]')
      .forEach((m) => m.remove())
    let meta = document.querySelector<HTMLMetaElement>(
      'meta[name="theme-color"]:not([media])',
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
