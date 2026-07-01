'use client'

import LogoIcon from '@/components/Brand/logos/LogoIcon'
import LogoType from '@/components/Brand/logos/LogoType'

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
  logoVariant?: 'icon' | 'logotype'
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
  const { resolvedTheme, setTheme } = useTheme()
  const [spinning, setSpinning] = useState(false)

  const handleThemeClick: MouseEventHandler<HTMLElement> = useCallback(
    (e) => {
      e.preventDefault()
      e.stopPropagation()
      // Spin the mark once as the theme flips (reduced-motion users skip it).
      const reduced =
        typeof window !== 'undefined' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (!reduced) setSpinning(true)
      setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')
    },
    [resolvedTheme, setTheme],
  )

  const iconSize = size ?? 42
  const LogoComponent =
    logoVariant === 'logotype' ? (
      <LogoType
        className={twMerge(
          '-ml-2 text-black md:ml-0 dark:text-white',
          logoClassName,
        )}
        width={size ?? 100}
      />
    ) : spinning ? (
      // While the theme flips, play the pre-rendered 3D spinning-top animation
      // as a 36-frame sprite. On animationend we swap back to the crisp static
      // SVG. --spin-end / background-size scale to the rendered size.
      <span
        aria-hidden
        className="animate-logo-top-spin inline-block"
        onAnimationEnd={() => setSpinning(false)}
        style={
          {
            width: iconSize,
            height: iconSize,
            backgroundImage: 'url(/assets/brand/top-spin.webp)',
            backgroundRepeat: 'no-repeat',
            backgroundSize: `${SPIN_FRAMES * iconSize}px ${iconSize}px`,
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
          aria-label={togglesTheme ? 'Toggle dark mode' : undefined}
          onClick={togglesTheme ? handleThemeClick : undefined}
        >
          {LogoComponent}
        </div>
      )}
    </div>
  )
}
