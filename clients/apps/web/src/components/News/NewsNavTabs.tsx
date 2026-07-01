'use client'

import { useAuth } from '@/hooks'
import { useT } from '@/providers/locale'
import { motion } from 'motion/react'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { twMerge } from 'tailwind-merge'
import { useNewsColumn, type NewsTab } from './NewsColumnContext'

const PROMO_DASHBOARD_PATH = '/dashboard'

const TABS: {
  id: NewsTab
  labelKey: 'news.tabs.yourDeck' | 'news.tabs.trending'
}[] = [
  { id: 'focus', labelKey: 'news.tabs.yourDeck' },
  { id: 'trending', labelKey: 'news.tabs.trending' },
]

const entryButton =
  'cursor-pointer rounded-xl px-3 py-1 text-gray-500 transition-colors hover:text-black dark:text-neutral-400 dark:hover:text-white'

/** The original navbar pill: a frosted segmented control with For You /
 * Trending, plus "More" (opens the source palette) and "Promo". The active tab
 * is a raised card that slides between options. */
export const NewsNavTabs = () => {
  const { tab, setTab, setSearchOpen } = useNewsColumn()
  const { currentUser } = useAuth()
  const router = useRouter()
  const t = useT()

  // The active pill slides between tabs via a layout animation. On a refresh the
  // statically-rendered tab ("trending") is swapped to the persisted tab during
  // hydration, which would make the pill spring across on load — a visible jump.
  // Only enable the slide once the user actually picks a tab, so that initial
  // swap lands instantly where it belongs.
  const [interacted, setInteracted] = useState(false)
  const selectTab = (id: NewsTab) => {
    setInteracted(true)
    setTab(id)
  }

  // Promo is gated: signed-in users go straight to the dashboard; signed-out
  // users sign in first and are returned to the dashboard afterwards.
  const onPromo = () =>
    router.push(
      currentUser
        ? PROMO_DASHBOARD_PATH
        : `/auth?return_to=${encodeURIComponent(PROMO_DASHBOARD_PATH)}`,
    )

  return (
    <span className="glass-input flex max-w-full items-center gap-x-1 overflow-x-auto rounded-2xl p-1 text-sm whitespace-nowrap">
      {TABS.map(({ id, labelKey }) => {
        const active = tab === id
        return (
          <button
            key={id}
            type="button"
            onClick={() => selectTab(id)}
            className={twMerge(
              'relative cursor-pointer rounded-xl px-3 py-1 transition-colors',
              active
                ? 'text-black dark:text-white'
                : 'text-gray-500 hover:text-black dark:text-neutral-400 dark:hover:text-white',
            )}
          >
            {active && (
              <motion.span
                layoutId="newsColumnPill"
                transition={
                  interacted
                    ? { type: 'spring', stiffness: 420, damping: 34 }
                    : { duration: 0 }
                }
                className="absolute inset-0 rounded-xl bg-white/70 shadow-sm backdrop-blur-md dark:bg-white/15"
              />
            )}
            <span className="relative z-10">{t(labelKey)}</span>
          </button>
        )
      })}
      <button
        type="button"
        onClick={() => {
          // Sources followed in the palette land in "Your deck", so jump there
          // as it opens — otherwise new cards show on a tab you aren't viewing.
          selectTab('focus')
          setSearchOpen(true)
        }}
        className={entryButton}
      >
        {t('news.tabs.more')}
      </button>
      <button type="button" onClick={onPromo} className={entryButton}>
        {t('news.tabs.promo')}
      </button>
    </span>
  )
}
