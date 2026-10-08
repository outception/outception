'use client'

import { useT } from '@/providers/translate'
import { CONFIG } from '@/utils/config'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@outception-com/ui/components/ui/dropdown-menu'
import {
  LogOut,
  Package,
  PlusCircle,
  Settings2,
  ShieldCheck,
} from 'lucide-react'
import Link from 'next/link'
import type { ReactElement } from 'react'

/**
 * The signed-in reader's menu, behind the avatar in the nav pill. Its own
 * chunk: only signed-in readers ever load the menu stack, and NewsNavTabs
 * shows the same trigger while it arrives. The menu renders in a portal, so
 * the pill's sideways scroll box cannot clip it.
 */
export default function AccountMenu({
  trigger,
  email,
  isAdmin,
}: {
  trigger: ReactElement
  email: string
  isAdmin: boolean
}) {
  const t = useT()
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
      <DropdownMenuContent
        side="bottom"
        align="end"
        sideOffset={10}
        className="paper-panel min-w-[220px] rounded-xl border-0 bg-transparent p-1.5"
      >
        <div className="truncate px-2 py-1.5 text-xs text-gray-500 dark:text-gray-400">
          {email}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/launches/mine" className="flex items-center gap-x-2">
            <Package size={15} aria-hidden />
            <span>{t('accountNav.products')}</span>
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/launches/new" className="flex items-center gap-x-2">
            <PlusCircle size={15} aria-hidden />
            <span>{t('accountNav.submit')}</span>
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link
            href="/account/preferences"
            className="flex items-center gap-x-2"
          >
            <Settings2 size={15} aria-hidden />
            <span>{t('accountNav.preferences')}</span>
          </Link>
        </DropdownMenuItem>
        {isAdmin ? (
          <DropdownMenuItem asChild>
            <Link href="/account/review" className="flex items-center gap-x-2">
              <ShieldCheck size={15} aria-hidden />
              <span>{t('accountNav.review')}</span>
            </Link>
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <a
            href={`${CONFIG.BASE_URL}/v1/auth/logout`}
            className="flex items-center gap-x-2"
          >
            <LogOut size={15} aria-hidden />
            <span>{t('accountNav.logout')}</span>
          </a>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
