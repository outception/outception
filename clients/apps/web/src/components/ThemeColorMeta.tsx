'use client'

import {
  getWallThemeServerSnapshot,
  getWallThemeSnapshot,
  subscribeWallTheme,
} from '@/utils/wallTheme'
import { useTheme } from 'next-themes'
import { useEffect, useSyncExternalStore } from 'react'

// The wall theme is cycled by the logo, independent of the OS, so an
// OS-media <meta theme-color> would mismatch it. This keeps a single
// theme-color meta in sync with the *current wall theme and tone* — it
// tints the browser-tab status bar and Android Chrome's address bar to
// match the page. (A Home-Screen install uses the black-translucent status
// bar instead, so this doesn't affect the edge-to-edge look there.)
export const ThemeColorMeta = () => {
  const wallTheme = useSyncExternalStore(
    subscribeWallTheme,
    getWallThemeSnapshot,
    getWallThemeServerSnapshot,
  )
  const { resolvedTheme } = useTheme()

  useEffect(() => {
    // Self-heal the wall attribute (e.g. a legacy theme id from an old
    // session) so the CSS edition blocks always match a live id.
    if (document.documentElement.dataset.theme !== wallTheme.id) {
      document.documentElement.dataset.theme = wallTheme.id
    }
    // Until next-themes resolves the tone (undefined on the first client
    // render), leave the chrome the pre-hydration script already painted —
    // writing a 'light' fallback here would flash the status bar on every
    // dark-mode load.
    if (resolvedTheme !== 'light' && resolvedTheme !== 'dark') return
    let meta = document.querySelector<HTMLMetaElement>(
      'meta[name="theme-color"]',
    )
    if (!meta) {
      meta = document.createElement('meta')
      meta.name = 'theme-color'
      document.head.appendChild(meta)
    }
    meta.content = wallTheme.chrome[resolvedTheme]
  }, [wallTheme, resolvedTheme])

  return null
}
