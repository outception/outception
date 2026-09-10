'use client'

import { useT } from '@/providers/locale'
import { useNewsColumn } from './NewsColumnContext'
import { LanguagePicker } from './LanguagePicker'

const entryButton =
  'nav-pill-tab cursor-pointer px-3 py-1 [color:color-mix(in_srgb,var(--color-ink)_55%,transparent)] transition-[color,transform] duration-100 hover:[color:var(--color-ink)] active:scale-95 active:[color:var(--color-ink)] dark:[color:color-mix(in_srgb,var(--color-ink-night)_65%,transparent)] dark:hover:[color:var(--color-ink-night)] dark:active:[color:var(--color-ink-night)]'

/** The navbar pill: the "Your stack" label, "Cards" (opens the source palette),
 * and a language/country flag picker at the end. */
export const NewsNavTabs = () => {
  const { setSearchOpen, view } = useNewsColumn()
  const t = useT()

  return (
    <span
      // Over the mosaic the bar hangs from the top edge of the screen on a
      // solid paper surface: the inset tint it wears over the wall would leave
      // the labels competing with whatever headline is behind them, and the
      // page has to sweep away from it on an outside curve rather than meet it
      // at a corner. Two elements, because the surface and its curves have to
      // paint OUTSIDE the box that scrolls its tabs sideways on a narrow
      // screen - one box cannot both overflow and be clipped.
      className={`nav-pill relative inline-flex max-w-full ${
        view === 'zoom' ? 'nav-pill-floating' : 'paper-input'
      }`}
    >
      <span className="flex max-w-full items-center gap-x-1 overflow-x-auto p-1 text-sm whitespace-nowrap">
        <span className="nav-pill-tab relative px-3 py-1">
          <span className="tab-pill nav-pill-tab absolute inset-0" />
          <span className="relative z-10 font-serif text-black dark:text-white">
            {t('news.tabs.yourCards')}
          </span>
        </span>
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className={entryButton}
        >
          {t('news.tabs.more')}
        </button>
        <LanguagePicker />
      </span>
    </span>
  )
}
