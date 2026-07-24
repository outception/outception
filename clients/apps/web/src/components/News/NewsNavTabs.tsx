'use client'

import { useT } from '@/providers/locale'
import { useNewsColumn } from './NewsColumnContext'
import { LanguagePicker } from './LanguagePicker'

const entryButton =
  'cursor-pointer rounded-xl px-3 py-1 [color:color-mix(in_srgb,var(--color-ink)_55%,transparent)] transition-colors hover:[color:var(--color-ink)] dark:[color:color-mix(in_srgb,var(--color-ink-night)_65%,transparent)] dark:hover:[color:var(--color-ink-night)]'

/** The navbar pill: the "Your deck" label, "More" (opens the source palette),
 * and a language/country flag picker at the end. */
export const NewsNavTabs = () => {
  const { setSearchOpen } = useNewsColumn()
  const t = useT()

  return (
    <span className="paper-input flex max-w-full items-center gap-x-1 overflow-x-auto rounded-lg p-1 text-sm whitespace-nowrap">
      <span className="relative rounded-md px-3 py-1">
        <span className="tab-pill absolute inset-0 rounded-md" />
        <span className="relative z-10 font-serif text-black dark:text-white">
          {t('news.tabs.yourDeck')}
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
  )
}
