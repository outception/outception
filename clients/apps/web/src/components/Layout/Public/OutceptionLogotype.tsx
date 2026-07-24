'use client'

import LogoIcon from '@/components/Brand/logos/LogoIcon'
import LogoType from '@/components/Brand/logos/LogoType'

import { cycleWallTheme } from '@/utils/wallTheme'
import { useTheme } from 'next-themes'
import Link from 'next/link'
import { CSSProperties, MouseEventHandler, useCallback, useState } from 'react'
import { twMerge } from 'tailwind-merge'

// Frame count of /assets/brand/top-spin.webp (must match the sprite strip).
const SPIN_FRAMES = 36

// Block the native right-click menu on the mark so it can't be saved or
// downloaded directly.
const blockContextMenu: MouseEventHandler<HTMLElement> = (e) =>
  e.preventDefault()

export const OutceptionLogotype = ({
  logoVariant = 'icon',
  size,
  className,
  logoClassName,
  href,
  togglesTheme = false,
}: {
  /**
   * 'icon' = the gem alone; 'logotype' = the brand SVG wordmark;
   * 'nameplate' = newspaper-style: the gem shrunk to a printer's ornament
   * beside a serif wordmark, matching the wall's newsprint look.
   */
  logoVariant?: 'icon' | 'logotype' | 'nameplate'
  size?: number
  className?: string
  logoClassName?: string
  href?: string
  /**
   * When set, left-clicking the logo toggles light/dark theme (the mark plays a
   * pre-rendered 3D spinning-top animation as it flips).
   */
  togglesTheme?: boolean
}) => {
  const { setTheme } = useTheme()
  const [spinning, setSpinning] = useState(false)

  const handleThemeClick: MouseEventHandler<HTMLElement> = useCallback(
    (e) => {
      e.preventDefault()
      e.stopPropagation()
      // Spin the mark once as the theme changes (reduced-motion users skip it).
      const reduced =
        typeof window !== 'undefined' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (!reduced) setSpinning(true)
      // The 12-stop wheel: each click shows the current edition's other
      // tone first (light → dark), then moves to the next edition —
      // Daybreak ☀ → Daybreak ☾ → Midnight ☀ → … — so every look is
      // reachable with the logo alone. Read the live tone from the DOM
      // class (next-themes' resolvedTheme lags a render, so back-to-back
      // clicks would otherwise repeat a stop).
      const currentTone = document.documentElement.classList.contains('dark')
        ? 'dark'
        : 'light'
      const { tone } = cycleWallTheme(currentTone)
      setTheme(tone)
    },
    [setTheme],
  )

  const iconSize = logoVariant === 'nameplate' ? (size ?? 18) : (size ?? 42)
  const IconComponent = spinning ? (
    // While the theme flips, play the original pre-rendered 3D spinning-top
    // animation (36-frame sprite: off-axis wobble + precession). The sprite
    // is used as an alpha MASK over a gradient fill that mirrors the gem's
    // shading — light dome above, a darker seam band across the middle, the
    // underside tail below — so the spinning top keeps the 3D look and the
    // seam. On animationend we swap back to the crisp static SVG.
    <span
      aria-hidden
      className="animate-logo-top-spin inline-block"
      onAnimationEnd={() => setSpinning(false)}
      style={
        {
          width: iconSize,
          height: iconSize,
          backgroundImage:
            'linear-gradient(180deg, var(--color-brand-200) 0%, var(--color-brand-400) 34%, var(--color-brand-500) 46%, var(--color-brand-900) 50%, var(--color-brand-700) 54%, var(--color-brand-500) 70%, var(--color-brand-300) 100%)',
          WebkitMaskImage: 'url(/assets/brand/top-spin.webp)',
          maskImage: 'url(/assets/brand/top-spin.webp)',
          WebkitMaskRepeat: 'no-repeat',
          maskRepeat: 'no-repeat',
          WebkitMaskSize: `${SPIN_FRAMES * iconSize}px ${iconSize}px`,
          maskSize: `${SPIN_FRAMES * iconSize}px ${iconSize}px`,
          '--spin-end': `-${SPIN_FRAMES * iconSize}px`,
        } as CSSProperties
      }
    />
  ) : (
    <LogoIcon
      className={twMerge('text-black dark:text-white', logoClassName)}
      size={iconSize}
    />
  )

  const LogoComponent =
    logoVariant === 'logotype' ? (
      <LogoType
        className={twMerge(
          '-ml-2 text-black md:ml-0 dark:text-white',
          logoClassName,
        )}
        width={size ?? 100}
      />
    ) : logoVariant === 'nameplate' ? (
      // Newspaper nameplate: the gem as a printer's ornament, then the title
      // in the wall's headline serif — small-scale front-page anatomy.
      <span className="inline-flex items-center gap-2">
        {IconComponent}
        <span className="font-serif text-2xl leading-none font-bold tracking-tight text-black dark:text-white">
          Outception
        </span>
      </span>
    ) : (
      IconComponent
    )

  return (
    <div
      className={twMerge('relative flex flex-row items-center', className)}
      onContextMenu={blockContextMenu}
    >
      {/* Warm the spin sprite so the first click animates without a download
          stall. Next hoists this <link> into <head>. */}
      {togglesTheme && (
        <link rel="prefetch" href="/assets/brand/top-spin.webp" as="image" />
      )}
      {href && !togglesTheme ? (
        <Link
          href={href}
          draggable={false}
          className="select-none"
          aria-label="Outception"
        >
          {LogoComponent}
        </Link>
      ) : (
        <div
          draggable={false}
          className={twMerge(
            'select-none',
            togglesTheme ? 'cursor-pointer' : '',
          )}
          aria-label={togglesTheme ? 'Change edition' : undefined}
          onClick={togglesTheme ? handleThemeClick : undefined}
        >
          {LogoComponent}
        </div>
      )}
    </div>
  )
}
