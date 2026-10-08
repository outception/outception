'use client'

import LogoIcon from '@/components/Brand/logos/LogoIcon'
import TopbarRight from '@/components/Layout/Public/TopbarRight'
import { useAuth } from '@/hooks/auth'
import { useT } from '@/providers/translate'
import { CONFIG } from '@/utils/config'
import { Avatar } from '@outception-com/orbit/Avatar'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from '@outception-com/ui/components/atoms/Sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@outception-com/ui/components/ui/dropdown-menu'
import {
  ArrowLeft,
  ChevronDown,
  LogOut,
  Package,
  PlusCircle,
  Settings2,
  ShieldCheck,
  TrendingUp,
  UserRound,
  type LucideIcon,
} from 'lucide-react'
import Link from 'next/link'
import { useHoldsEnvironment } from '@/utils/motion'
import { usePathname } from 'next/navigation'
import { PropsWithChildren } from 'react'
import { twMerge } from 'tailwind-merge'

type Item = { href: string; label: string; icon: LucideIcon }

// The item styles mirror the dashboard this area is modelled on: the open
// page is a raised white card with a hairline, the others are quiet text
// that darkens on hover.
const itemBase =
  'flex flex-row items-center rounded-lg border border-transparent px-2 transition-colors'
const itemActive = 'tab-pill text-black dark:text-white'
const itemQuiet =
  'dark:text-outception-500 dark:hover:text-outception-200 text-gray-500 hover:text-black'

/** The signed-in reader's area, laid out like a dashboard: a collapsible
 * sidebar with the mark, the way back to the wall, the reader's pages and
 * the reader's own menu at the foot; the page in a white inset beside it
 * with its title. The wall itself is not here: a signed-in reader keeps the
 * public wall, and the person icon on it leads here. */
export const AccountLayout = ({ children }: PropsWithChildren) => {
  const pathname = usePathname()
  const { currentUser } = useAuth()
  const t = useT()
  const isAdmin = !!currentUser?.is_admin
  // The chart on the analytics page follows the same motion rules as the
  // wall: a hidden tab or reduced motion pauses it.
  useHoldsEnvironment()
  const items: Item[] = [
    { href: '/launches/mine', label: t('accountNav.products'), icon: Package },
    {
      href: '/launches/analytics',
      label: t('accountNav.analytics'),
      icon: TrendingUp,
    },
    { href: '/launches/new', label: t('accountNav.submit'), icon: PlusCircle },
    {
      href: '/account/preferences',
      label: t('accountNav.preferences'),
      icon: Settings2,
    },
    ...(isAdmin
      ? [
          {
            href: '/account/review',
            label: t('accountNav.review'),
            icon: ShieldCheck,
          },
        ]
      : []),
  ]
  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`)
  const current = items.find((item) => isActive(item.href))

  return (
    <SidebarProvider className="account-shell" defaultOpen={false}>
      <div className="relative flex min-h-dvh w-full flex-col md:flex-row md:p-2">
        {/* Small screens: a bar with the mark, the reader's menu and the
            sidebar trigger; the sidebar itself slides in as a sheet. */}
        <Box
          display={{ base: 'flex', md: 'none' }}
          alignItems="center"
          justifyContent="between"
          paddingHorizontal="l"
          paddingVertical="m"
        >
          <Link href="/" aria-label="Outception home">
            <LogoIcon size={38} />
          </Link>
          <Box alignItems="center" columnGap="m">
            <TopbarRight authenticatedUser={currentUser} />
            <SidebarTrigger />
          </Box>
        </Box>
        <div className="hidden md:flex">
          <Sidebar variant="inset" collapsible="icon">
            <SidebarHeader className="flex flex-row items-center justify-between md:pt-3.5">
              <Link
                href="/"
                aria-label="Outception home"
                className="px-1 group-data-[collapsible=icon]:hidden"
              >
                <LogoIcon size={38} />
              </Link>
              {/* The visible way to fold the sidebar to its icons and back;
                  the rail on the edge and the keyboard shortcut still work. */}
              <SidebarTrigger
                title={t('accountNav.sidebar')}
                aria-label={t('accountNav.sidebar')}
              />
            </SidebarHeader>
            <SidebarContent className="gap-4 px-2 py-2">
              <SidebarMenu>
                <SidebarMenuItem className="mb-4">
                  <SidebarMenuButton tooltip={t('accountNav.wall')} asChild>
                    <Link href="/" className={twMerge(itemBase, itemQuiet)}>
                      <ArrowLeft size={15} aria-hidden />
                      <span className="ml-2 text-sm font-medium">
                        {t('accountNav.wall')}
                      </span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                {items.map((item) => {
                  const active = isActive(item.href)
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        tooltip={item.label}
                        isActive={active}
                        asChild
                      >
                        <Link
                          href={item.href}
                          prefetch
                          className={twMerge(
                            itemBase,
                            active ? itemActive : itemQuiet,
                          )}
                        >
                          <item.icon size={15} aria-hidden />
                          <span className="ml-2 text-sm font-medium">
                            {item.label}
                          </span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarContent>
            <SidebarFooter>
              {currentUser ? (
                <SidebarMenu>
                  <SidebarMenuItem>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <SidebarMenuButton>
                          <Avatar
                            name={currentUser.email}
                            avatar_url={currentUser.avatar_url}
                            className="h-6 w-6"
                          />
                          <span className="min-w-0 truncate text-sm">
                            {currentUser.email}
                          </span>
                          <ChevronDown
                            size={15}
                            className="ml-auto"
                            aria-hidden
                          />
                        </SidebarMenuButton>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent
                        side="top"
                        align="center"
                        className="paper-panel w-(--radix-popper-anchor-width) min-w-[220px] rounded-xl border-0 bg-transparent p-1.5"
                      >
                        <DropdownMenuItem asChild>
                          <Link
                            href="/account/preferences"
                            className="flex flex-row items-center gap-x-2"
                          >
                            <UserRound size={15} aria-hidden />
                            <span>{t('accountNav.account')}</span>
                          </Link>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem asChild>
                          <a
                            href={`${CONFIG.BASE_URL}/v1/auth/logout`}
                            className="flex flex-row items-center gap-x-2"
                          >
                            <LogOut size={15} aria-hidden />
                            <span>{t('accountNav.logout')}</span>
                          </a>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </SidebarMenuItem>
                </SidebarMenu>
              ) : null}
            </SidebarFooter>
            <SidebarRail />
          </Sidebar>
        </div>
        <SidebarInset className="paper-sheet bg-transparent md:rounded-2xl">
          <Box
            as="main"
            flexDirection="column"
            flexGrow={1}
            width="100%"
            padding={{ base: 'l', md: '2xl' }}
            rowGap="xl"
          >
            {current ? (
              <Text variant="heading-s" as="h1">
                {current.label}
              </Text>
            ) : null}
            {children}
          </Box>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}
