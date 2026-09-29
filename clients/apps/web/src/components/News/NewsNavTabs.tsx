'use client'

import { WallThemeSwatches } from '@/components/Layout/Public/WallThemeSwatches'
import { useT } from '@/providers/translate'
import { setWallTheme, type WallThemeTone } from '@/utils/wallTheme'
import { Settings } from 'lucide-react'
import { useTheme } from 'next-themes'
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import { useNewsColumn } from './NewsColumnContext'

/** The four places in the pill the raised chip can sit. */
type NavItem = 'stack' | 'cards' | 'settings'

const item =
  'nav-pill-tab relative z-10 cursor-pointer px-3 py-1 transition-[color,transform] duration-100 active:scale-95'
const muted =
  '[color:color-mix(in_srgb,var(--color-ink)_55%,transparent)] hover:[color:var(--color-ink)] dark:[color:color-mix(in_srgb,var(--color-ink-night)_65%,transparent)] dark:hover:[color:var(--color-ink-night)]'
const lit = 'text-black dark:text-white'

/**
 * The navbar pill: "Your stack", "Cards" (opens the source palette), and the
 * settings gear that opens the edition fan.
 *
 * The raised chip is ONE element that slides between them rather than a
 * highlight baked into the first tab. It marks what the reader has OPEN, not
 * what the wall is showing: underneath it is always their stack, so while the
 * palette is up the chip sits there, and it slides back to "Your stack" the
 * moment they close it.
 */
export const NewsNavTabs = () => {
  const { searchOpen, setSearchOpen } = useNewsColumn()
  const t = useT()
  const { setTheme } = useTheme()
  const [settingsOpen, setSettingsOpen] = useState(false)

  const active: NavItem = searchOpen
    ? 'cards'
    : settingsOpen
      ? 'settings'
      : 'stack'

  const rootRef = useRef<HTMLSpanElement>(null)
  const markerRef = useRef<HTMLSpanElement>(null)
  const items = useRef<Partial<Record<NavItem, HTMLElement | null>>>({})

  // Drive the chip straight onto the element rather than through state: it has
  // to follow label widths, and
  // measuring into state would cost a render on every one of those.
  useLayoutEffect(() => {
    const target = items.current[active]
    const marker = markerRef.current
    if (!target || !marker) return
    marker.style.left = `${target.offsetLeft}px`
    marker.style.width = `${target.offsetWidth}px`
  })

  // The live tone, read off the root class rather than next-themes'
  // `resolvedTheme`, which lags a render - the ring would sit on the wrong
  // swatch for a frame after every pick. Same as the logo's own fan.
  const [tone, setTone] = useState<WallThemeTone>('light')
  useEffect(() => {
    const read = () =>
      setTone(
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

  const selectTheme = useCallback(
    (id: string, nextTone: WallThemeTone) => {
      setWallTheme(id)
      setTheme(nextTone)
    },
    [setTheme],
  )

  // Escape closes the fan, and so does a pointer anywhere else: it hangs over
  // the wall, so leaving it open would swallow taps meant for the cards.
  useEffect(() => {
    if (!settingsOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSettingsOpen(false)
    }
    const onDown = (e: PointerEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setSettingsOpen(false)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onDown)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onDown)
    }
  }, [settingsOpen])

  return (
    <span
      ref={rootRef}
      // The bar hangs from the top edge of the screen on a solid paper
      // surface: an inset tint would leave the labels competing with whatever
      // headline sat behind them.
      className="nav-pill nav-pill-floating relative inline-flex max-w-full"
    >
      {/* The sideways scroll for narrow screens lives here, not on the pill:
          the surface, its curves and the fan all have to paint OUTSIDE this
          box, and one box cannot both overflow and be clipped. */}
      <span className="relative flex max-w-full items-center gap-x-1 overflow-x-auto p-1 text-sm whitespace-nowrap">
        <span ref={markerRef} className="nav-pill-marker tab-pill" />
        <button
          type="button"
          ref={(el) => {
            items.current.stack = el
          }}
          onClick={() => setSearchOpen(false)}
          className={`${item} font-serif ${active === 'stack' ? lit : muted}`}
        >
          {t('news.tabs.yourCards')}
        </button>
        <button
          type="button"
          ref={(el) => {
            items.current.cards = el
          }}
          onClick={() => setSearchOpen(true)}
          className={`${item} ${active === 'cards' ? lit : muted}`}
        >
          {t('news.tabs.more')}
        </button>
        <button
          type="button"
          ref={(el) => {
            items.current.settings = el
          }}
          onClick={() => setSettingsOpen((was) => !was)}
          aria-expanded={settingsOpen}
          aria-label={t('news.cards.changeEdition')}
          title={t('news.cards.changeEdition')}
          className={`${item} flex items-center ${
            active === 'settings' ? lit : muted
          }`}
        >
          <Settings size={15} aria-hidden />
        </button>
      </span>

      {/* The hinge of the fan: a swatch-sized box centred under the pill. The
          fan measures its light row off this box's left edge and its dark row
          off its right, so the box is the middle of the fan, the way the logo
          used to be. */}
      <span className="nav-pill-fan">
        <WallThemeSwatches
          open={settingsOpen}
          tone={tone}
          onSelect={selectTheme}
        />
      </span>
    </span>
  )
}
