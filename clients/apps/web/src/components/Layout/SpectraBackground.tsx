'use client'

import { useTheme } from 'next-themes'
import dynamic from 'next/dynamic'

// Our own WebGL gradient — paints in an effect, so load it client-only.
const SpectraCanvas = dynamic(() => import('./SpectraCanvas'), { ssr: false })
// The radial dot field also paints to a canvas in an effect — client-only too.
const SpectraDots = dynamic(() => import('./SpectraDots'), { ssr: false })

// The one Spectra background, in two outfits. Light is a calm cream wash —
// closely-spaced morning-mist / cream tones so the drift reads as a soft,
// slowly-shifting warm neutral rather than a loud gradient. Dark is the same
// look inverted: near-black warm neutrals on a near-black base. Clicking the
// logo flips the theme, which swaps the palette here.
const LIGHT_PALETTE = ['#fdfbf7', '#f7f4ed', '#f1ece1', '#faf3e6', '#efe9db']
const DARK_PALETTE = ['#0c0c0c', '#161514', '#201c1a', '#121110', '#0e0e0e']

/** Spectra: the app's single living background — a soft, slowly-flowing neutral
 * gradient rendered by our own WebGL shader (see SpectraCanvas), fixed behind
 * everything (the glass surfaces backdrop-blur it). A faint static dot grid sits
 * on top (light grey dots on cream; inverted to light dots on near-black for
 * dark). It has a light and a dark variant; the
 * logo's click toggles the theme between them. pointer-events-none so it never
 * intercepts input. */
export const SpectraBackground = () => {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'
  const colors = isDark ? DARK_PALETTE : LIGHT_PALETTE

  return (
    <div
      aria-hidden
      className={
        // Static CSS wash underneath, themed via the `dark:` variant. next-themes
        // sets the .dark class before first paint, so this is already the right
        // colour when the page loads — it fills the gap until the WebGL canvas
        // paints its first frame, killing any flash.
        'pointer-events-none fixed inset-0 -z-10 overflow-hidden ' +
        'bg-[radial-gradient(130%_130%_at_25%_20%,#fdfbf7_0%,#f4efe4_55%,#efe9db_100%)] ' +
        'dark:bg-[radial-gradient(130%_130%_at_25%_20%,#161514_0%,#0f0e0d_55%,#0a0a0a_100%)]'
      }
    >
      {/* key on the theme so the shader restarts cleanly with the new palette. */}
      <SpectraCanvas key={isDark ? 'dark' : 'light'} colors={colors} />
      {/* Dot field — a uniform grid whose dots fade out from a focal point, so
          the texture reads as concentrated then thinning toward the edges (no
          ring/spoke artifacts). Grey on the cream wash, white for dark. */}
      <SpectraDots
        key={isDark ? 'dark-dots' : 'light-dots'}
        color={isDark ? '#ffffff' : '#9aa1ab'}
        maxOpacity={isDark ? 0.16 : 0.55}
      />
    </div>
  )
}
