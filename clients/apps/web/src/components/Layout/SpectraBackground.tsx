'use client'

import { useTheme } from 'next-themes'
import dynamic from 'next/dynamic'

// Our own WebGL gradient — paints in an effect, so load it client-only.
const SpectraCanvas = dynamic(() => import('./SpectraCanvas'), { ssr: false })
// The radial line grid also paints to a canvas in an effect — client-only too.
const SpectraGrid = dynamic(() => import('./SpectraGrid'), { ssr: false })

// The one Spectra background, in two outfits. Light is a warm cream→peach wash
// (matching dub's landing hero) — closely-spaced apricot/cream tones so the
// drift reads as a soft, slowly-shifting warm glow rather than a loud gradient.
// Dark is the same look inverted: near-black warm neutrals on a near-black base.
// Clicking the logo flips the theme, which swaps the palette here.
const LIGHT_PALETTE = ['#ffffff', '#fdf9f4', '#fbf1e6', '#fdf6ee', '#faf0e4']
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
        'bg-[radial-gradient(120%_120%_at_50%_100%,#fbe7d2_0%,#fdf4ec_45%,#ffffff_100%)] ' +
        'dark:bg-[radial-gradient(130%_130%_at_25%_20%,#161514_0%,#0f0e0d_55%,#0a0a0a_100%)]'
      }
    >
      {/* key on the theme so the shader restarts cleanly with the new palette. */}
      <SpectraCanvas key={isDark ? 'dark' : 'light'} colors={colors} />
      {/* Line grid (dub-style squares) — a uniform grid whose lines fade out
          from a focal point, so the texture reads as concentrated then thinning
          toward the edges. Golden yellow on the cream wash (matching dub's warm
          accent), white for dark. */}
      <SpectraGrid
        key={isDark ? 'dark-grid' : 'light-grid'}
        color={isDark ? '#ffffff' : '#f0b429'}
        maxOpacity={isDark ? 0.14 : 0.28}
      />
    </div>
  )
}
