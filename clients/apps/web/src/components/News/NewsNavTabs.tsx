'use client'

import { useAuth } from '@/hooks/auth'
import { useT } from '@/providers/translate'
import { Avatar } from '@outception-com/orbit/Avatar'
import { UserRound } from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Suspense, lazy, useLayoutEffect, useRef } from 'react'

import { useNewsColumn } from './NewsColumnContext'

// The menu stack loads only for signed-in readers; see AccountMenu.
const AccountMenu = lazy(() => import('./AccountMenu'))

/** The places in the pill the raised chip can sit. */
type NavItem = 'stack' | 'cards' | 'account'

/** Where readers talk about the product: the repository's discussions. */

const item =
  'nav-pill-tab relative z-10 cursor-pointer px-3 py-1 transition-[color,transform] duration-100 active:scale-95'
const muted =
  '[color:color-mix(in_srgb,var(--color-ink)_55%,transparent)] hover:[color:var(--color-ink)] dark:[color:color-mix(in_srgb,var(--color-ink-night)_65%,transparent)] dark:hover:[color:var(--color-ink-night)]'
const lit = 'text-black dark:text-white'

/**
 * The navbar pill: "Your stack", "Cards" (opens the source palette), and the
 * reader's door: sign in, or their account once they have. The edition is
 * changed by pressing the mark under the bar.
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
  const pathname = usePathname()
  const { currentUser } = useAuth()
  const isAdmin = !!currentUser?.is_admin
  const onAccount =
    (pathname?.startsWith('/account') || pathname?.startsWith('/auth')) ?? false
  const offWall = onAccount

  const active: NavItem = searchOpen ? 'cards' : onAccount ? 'account' : 'stack'

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

  const accountTrigger = currentUser ? (
    <button
      type="button"
      ref={(el) => {
        items.current.account = el
      }}
      aria-label={t('news.tabs.account')}
      title={currentUser.email}
      className={`${item} flex items-center ${
        active === 'account' ? lit : muted
      }`}
    >
      <Avatar
        name={currentUser.email}
        avatar_url={currentUser.avatar_url}
        className="h-5 w-5 text-[10px]"
      />
    </button>
  ) : null

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
        {offWall ? (
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
        {currentUser && accountTrigger ? (
          // Signed in: the reader's own face, opening their pages and the
          // way out. The bare trigger stands in while the menu's chunk loads.
          <Suspense fallback={accountTrigger}>
            <AccountMenu
              trigger={accountTrigger}
              email={currentUser.email}
              isAdmin={isAdmin}
            />
          </Suspense>
        ) : (
          <Link
            href="/auth"
            ref={(el) => {
              items.current.account = el
            }}
            aria-label={t('news.tabs.signIn')}
            title={t('news.tabs.signIn')}
            className={`${item} flex items-center ${
              active === 'account' ? lit : muted
            }`}
          >
            <UserRound size={15} aria-hidden />
          </Link>
        )}
      </span>
    </span>
  )
}
