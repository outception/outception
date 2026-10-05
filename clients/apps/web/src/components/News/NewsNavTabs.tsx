'use client'

import { WallThemeSwatches } from '@/components/Layout/Public/WallThemeSwatches'
import { useT } from '@/providers/translate'
import {
  WALL_LOOKS,
  getWallLookServerSnapshot,
  getWallLookSnapshot,
  setWallLook,
  setWallTheme,
  subscribeWallTheme,
  type WallThemeTone,
} from '@/utils/wallTheme'
import { briefingPath } from '@outception-com/news-core'
import { Settings } from 'lucide-react'
import { useTheme } from 'next-themes'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from 'react'
import { TellUsSheet } from '@/components/Landing/TellUsSheet'
import { useNewsColumn } from './NewsColumnContext'
import { FLAGS, toggleFlag, useFlags } from './readerStores'
import {
  getBriefingProfilesSnapshot,
  getBriefingProfilesServerSnapshot,
  subscribe,
} from './newsPrefsStore'

/** The places in the pill the raised chip can sit. */
type NavItem = 'stack' | 'cards' | 'briefing' | 'settings'

/** The briefing the pill opens: the first profile the reader follows, else
 * the house default. */
const DEFAULT_BRIEFING_PROFILE = 'news-junkie'

/** The reading switches beside the looks: hide what was read, one row per
 * story or every outlet, and the way to tell us something. */
const ReadingControls = ({ open }: { open: boolean }) => {
  const t = useT()
  const flags = useFlags()
  const hideRead = flags.includes(FLAGS.hideRead)
  const everyOutlet = flags.includes(FLAGS.showEveryOutlet)
  const autoplay = flags.includes(FLAGS.autoplay)
  return (
    <span
      className="nav-pill-looks nav-pill-controls"
      data-open={open}
      aria-hidden={!open}
      role="group"
      aria-label={t('news.controls.label')}
    >
      <button
        type="button"
        className="ghost-pill"
        aria-pressed={hideRead}
        data-active={hideRead}
        tabIndex={open ? 0 : -1}
        onClick={() => toggleFlag(FLAGS.hideRead)}
      >
        {t('news.controls.hideRead')}
      </button>
      <button
        type="button"
        className="ghost-pill"
        aria-pressed={everyOutlet}
        data-active={everyOutlet}
        tabIndex={open ? 0 : -1}
        onClick={() => toggleFlag(FLAGS.showEveryOutlet)}
      >
        {everyOutlet
          ? t('news.controls.everyOutlet')
          : t('news.controls.oneRowPerStory')}
      </button>
      <button
        type="button"
        className="ghost-pill"
        aria-pressed={autoplay}
        data-active={autoplay}
        tabIndex={open ? 0 : -1}
        onClick={() => toggleFlag(FLAGS.autoplay)}
      >
        {t('news.controls.autoplay')}
      </button>
      <TellUsSheet trigger="pill" />
    </span>
  )
}

/** The look row under the fan: three CSS-only treatments, plain first. */
const LookPicker = ({ open }: { open: boolean }) => {
  const t = useT()
  const active = useSyncExternalStore(
    subscribeWallTheme,
    getWallLookSnapshot,
    getWallLookServerSnapshot,
  )
  const labels: Record<string, string> = {
    plain: t('news.looks.plain'),
    noir: t('news.looks.noir'),
    night: t('news.looks.night'),
  }
  return (
    <span
      className="nav-pill-looks"
      data-open={open}
      aria-hidden={!open}
      role="group"
      aria-label={t('news.looks.label')}
    >
      {WALL_LOOKS.map((look) => (
        <button
          key={look.id}
          type="button"
          className="ghost-pill"
          aria-pressed={active.id === look.id}
          tabIndex={open ? 0 : -1}
          onClick={() => setWallLook(look.id)}
          data-active={active.id === look.id}
        >
          {labels[look.id] ?? look.label}
        </button>
      ))}
    </span>
  )
}

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
  const pathname = usePathname()
  const onBriefing = pathname?.startsWith('/briefing') ?? false
  const profiles = useSyncExternalStore(
    subscribe,
    getBriefingProfilesSnapshot,
    getBriefingProfilesServerSnapshot,
  )
  const briefingHref = briefingPath(profiles[0] ?? DEFAULT_BRIEFING_PROFILE)

  const active: NavItem = searchOpen
    ? 'cards'
    : settingsOpen
      ? 'settings'
      : onBriefing
        ? 'briefing'
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
        {onBriefing ? (
          <Link
            href="/"
            ref={(el) => {
              items.current.stack = el
            }}
            className={`${item} font-serif ${active === 'stack' ? lit : muted}`}
          >
            {t('news.tabs.yourCards')}
          </Link>
        ) : (
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
        )}
        <Link
          href={briefingHref}
          ref={(el) => {
            items.current.briefing = el
          }}
          className={`${item} ${active === 'briefing' ? lit : muted}`}
        >
          {t('news.tabs.briefing')}
        </Link>
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
      <LookPicker open={settingsOpen} />
      <ReadingControls open={settingsOpen} />
    </span>
  )
}
