'use client'

import LogoIcon from '@/components/Brand/logos/LogoIcon'
import LogoType from '@/components/Brand/logos/LogoType'

import { useT } from '@/providers/locale'
import { setWallTheme, type WallThemeTone } from '@/utils/wallTheme'
import { WallThemeSwatches } from './WallThemeSwatches'
import { useTheme } from 'next-themes'
import Link from 'next/link'
import {
  CSSProperties,
  MouseEventHandler,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
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
  const t = useT()
  const [spinning, setSpinning] = useState(false)
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  // The live tone, read off the root class rather than next-themes'
  // `resolvedTheme`, which lags a render - the ring would sit on the wrong
  // swatch for a frame after every pick.
  const [tone, setToneState] = useState<WallThemeTone>('light')
  useEffect(() => {
    const read = () =>
      setToneState(
        document.documentElement.classList.contains('dark') ? 'dark' : 'light',
      )
    read()
    const observer = new MutationObserver(read)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    })
    return () => observer.disconnect()
  }, [])

  const handleThemeClick: MouseEventHandler<HTMLElement> = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    // Spin the mark as the fan opens (reduced-motion users skip it).
    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (!reduced) setSpinning(true)
    // The logo no longer steps a wheel. It opens the fan, where every edition
    // is one click away in both tones - stepping meant up to ten clicks to
    // reach a look, through nine nobody asked to see.
    setOpen((was) => !was)
  }, [])

  const handleSelect = useCallback(
    (id: string, nextTone: WallThemeTone) => {
      setWallTheme(id)
      setTheme(nextTone)
    },
    [setTheme],
  )

  // Escape closes, and so does a pointer anywhere else. The fan sits over the
  // wall, so leaving it open would swallow taps meant for the cards.
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    const onDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onDown)
    }
  }, [open])

  const iconSize = logoVariant === 'nameplate' ? (size ?? 18) : (size ?? 42)
  const IconComponent = spinning ? (
    // While the theme flips, play the original pre-rendered 3D spinning-top
    // animation (36-frame sprite: off-axis wobble + precession). The sprite
    // is used as an alpha MASK over a gradient fill that mirrors the gem's
    // shading - light dome above, a darker seam band across the middle, the
    // underside tail below - so the spinning top keeps the 3D look and the
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
      // in the wall's headline serif - small-scale front-page anatomy.
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
      ref={rootRef}
      className={twMerge('relative flex flex-row items-center', className)}
      onContextMenu={blockContextMenu}
    >
      {togglesTheme && (
        <WallThemeSwatches open={open} tone={tone} onSelect={handleSelect} />
      )}
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
      ) : togglesTheme ? (
        // A real <button>, not a clickable <div>. It performs an action rather
        // than navigating, so this is what it always should have been - and
        // the wall's game strip sets `pointer-events: none` on itself and
        // hands them back only to `button` and `a`, so as a div the logo was
        // simply dead wherever the strip wrapped it. It is also now keyboard
        // reachable, which a div with an onClick never was.
        <button
          type="button"
          draggable={false}
          className={twMerge(
            'cursor-pointer appearance-none border-0 bg-transparent p-0 select-none',
          )}
          aria-label={t('news.cards.changeEdition')}
          aria-expanded={open}
          onClick={handleThemeClick}
        >
          {LogoComponent}
        </button>
      ) : (
        <div draggable={false} className="select-none">
          {LogoComponent}
        </div>
      )}
    </div>
  )
}
