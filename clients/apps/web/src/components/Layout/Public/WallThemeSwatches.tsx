'use client'

import {
  WALL_THEMES,
  getWallThemeServerSnapshot,
  getWallThemeSnapshot,
  subscribeWallTheme,
  type WallThemeTone,
} from '@/utils/wallTheme'
import { useSyncExternalStore } from 'react'
import { useOptionalNewsColumn } from '@/components/News/NewsColumnContext'
import { useT } from '@/providers/locale'

/**
 * The edition picker the logo fans out: every light face to the LEFT of the
 * mark, every dark face to the RIGHT.
 *
 * The logo used to step a ten-stop wheel, so the look you wanted was up to ten
 * clicks away and you had to pass through nine you did not want to see. Every
 * stop is now one click, and the swatch IS the colour it applies: each edition
 * already carries the exact page colour for both tones (`chrome`), which is
 * the same value the browser chrome and the wall use, so a swatch can never
 * drift from what it promises.
 *
 * Light faces sit left and dark faces sit right, which also reads as a dial
 * running from lightest to darkest across the mark.
 */
export const WallThemeSwatches = ({
  open,
  tone,
  onSelect,
}: {
  open: boolean
  /** The live tone, read from the DOM by the caller (next-themes lags a render). */
  tone: WallThemeTone
  onSelect: (id: string, tone: WallThemeTone) => void
}) => {
  const active = useSyncExternalStore(
    subscribeWallTheme,
    getWallThemeSnapshot,
    getWallThemeServerSnapshot,
  )
  const t = useT()
  // Optional on purpose: this same logo renders in the dashboard layouts,
  // where there is no wall to switch. Asking without requiring lets the fan
  // simply omit the control there instead of throwing.
  const column = useOptionalNewsColumn()

  const row = (rowTone: WallThemeTone) =>
    // Straight down the edition list, identical on both sides: grey, blue,
    // purple, green, cream. Sorting by lightness was tried and thrown out -
    // it reshuffled the editions into an order nobody recognised.
    WALL_THEMES.map((theme, i) => {
      const isActive = theme.id === active.id && rowTone === tone
      // Index IS the distance from the mark on both sides: the left row lays
      // its children out right-to-left (`flex-row-reverse`), so its first
      // child lands nearest the logo just as the right row's does. Reversing
      // the array as well would double the flip and stand the fan backwards.
      const step = i
      return (
        <button
          key={`${rowTone}-${theme.id}`}
          type="button"
          onClick={() => onSelect(theme.id, rowTone)}
          aria-label={`${theme.label}, ${rowTone}`}
          aria-pressed={isActive}
          title={`${theme.label} ${rowTone}`}
          tabIndex={open ? 0 : -1}
          className={
            // 24px on a roomy screen, stepping down to 20 and 18 so all ten
            // plus the mark still fit inside a 320px phone. 32px matched the
            // logo exactly and read as too heavy beside it.
            'swatch relative h-[18px] w-[18px] shrink-0 cursor-pointer ' +
            'rounded-full border-2 sm:h-5 sm:w-5 md:h-6 md:w-6 ' +
            // The palest edition is nearly white, so on a light page the fill
            // says nothing and the border IS the swatch. Faint enough to stay
            // quiet on the vivid ones, strong enough to draw the pale one.
            'border-black/25 dark:border-white/25 ' +
            'focus-visible:ring-2 focus-visible:ring-current focus-visible:outline-none ' +
            (isActive ? 'is-active' : '')
          }
          style={{
            backgroundColor: theme.chrome[rowTone],
            ['--swatch-step' as string]: String(step),
            ['--swatch-last' as string]: String(WALL_THEMES.length - 1),
            ['--swatch-accent' as string]: theme.accent,
          }}
        >
          {/* The accent as an inner dot, so one circle carries BOTH halves of
              an edition: the page it paints and the colour the gem and links
              take with it. Proportional inset, so it holds at every size. */}
          <span
            aria-hidden="true"
            className="swatch-dot pointer-events-none absolute inset-[26%] rounded-full"
          />
        </button>
      )
    })

  return (
    <>
      <span
        // Not `hidden`, and not unmounted: both snap the fan away instantly,
        // and an unfurl that vanishes rather than retracting looks unfinished.
        // The open state drives CSS transitions instead, so closing plays in
        // reverse. `visibility` still leaves the tab order and the
        // accessibility tree, it just waits for the animation first.
        data-open={open}
        aria-hidden={!open}
        className="swatch-row swatch-row-left pointer-events-auto absolute top-1/2 right-full mr-1.5 flex -translate-y-1/2 flex-row-reverse items-center gap-1 sm:mr-2 sm:gap-1.5 md:mr-4 md:gap-2"
      >
        {row('light')}
      </span>
      <span
        data-open={open}
        aria-hidden={!open}
        className="swatch-row swatch-row-right pointer-events-auto absolute top-1/2 left-full ml-1.5 flex -translate-y-1/2 items-center gap-1 sm:ml-2 sm:gap-1.5 md:ml-4 md:gap-2"
      >
        {row('dark')}
        {column && (
          <button
            type="button"
            onClick={() =>
              column.setView(column.view === 'cards' ? 'zoom' : 'cards')
            }
            aria-label={
              column.view === 'cards'
                ? t('news.view.toZoom')
                : t('news.view.toCards')
            }
            aria-pressed={column.view === 'zoom'}
            tabIndex={open ? 0 : -1}
            // Last in the fan, past the dark faces: the swatches change how the
            // wall LOOKS, this changes what it shows, so it sits apart from
            // them rather than pretending to be another edition.
            className="swatch swatch-view relative h-[18px] w-[18px] shrink-0 cursor-pointer rounded-full border-2 border-black/25 sm:h-5 sm:w-5 md:h-6 md:w-6 dark:border-white/25"
            style={{
              ['--swatch-step' as string]: String(WALL_THEMES.length),
              ['--swatch-last' as string]: String(WALL_THEMES.length),
            }}
          >
            <svg
              viewBox="0 0 16 16"
              aria-hidden="true"
              className="absolute inset-[22%] h-auto w-auto"
              fill="currentColor"
            >
              {column.view === 'cards' ? (
                <>
                  <rect x="0" y="0" width="7" height="7" rx="1" />
                  <rect x="9" y="0" width="7" height="7" rx="1" />
                  <rect x="0" y="9" width="7" height="7" rx="1" />
                  <rect x="9" y="9" width="7" height="7" rx="1" />
                </>
              ) : (
                <rect x="1" y="1" width="14" height="14" rx="2" />
              )}
            </svg>
          </button>
        )}
      </span>
    </>
  )
}
