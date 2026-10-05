'use client'

import { OutceptionLogotype } from '@/components/Layout/Public/OutceptionLogotype'
import TopbarRight from '@/components/Layout/Public/TopbarRight'
import { useAuth } from '@/hooks/auth'
import { useT } from '@/providers/translate'
import { CONFIG } from '@/utils/config'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit/Text'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { PropsWithChildren } from 'react'

/** The signed-in reader's area: the wall with their follows, their
 * preferences, their submitted products, and the review queue for the
 * admin list. One narrow nav, no organizations. */
export const AccountLayout = ({ children }: PropsWithChildren) => {
  const pathname = usePathname()
  const { currentUser } = useAuth()
  const t = useT()
  const isAdmin =
    !!currentUser && CONFIG.ADMIN_EMAILS.includes(currentUser.email)
  const items: { href: string; label: string }[] = [
    { href: '/account/news', label: t('meta.news') },
    { href: '/account/preferences', label: t('meta.preferences') },
    { href: '/launches/mine', label: t('launches.mine.title') },
    ...(isAdmin
      ? [{ href: '/account/review', label: t('launches.review.title') }]
      : []),
  ]
  return (
    <Box flexDirection="column" minHeight="100vh">
      <Box
        as="header"
        alignItems="center"
        justifyContent="between"
        paddingHorizontal="l"
        paddingVertical="m"
        borderBottomWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
      >
        <OutceptionLogotype logoVariant="icon" size={32} togglesTheme />
        <TopbarRight authenticatedUser={currentUser} />
      </Box>
      <Box flexDirection={{ base: 'column', md: 'row' }} flexGrow={1}>
        <Box
          as="nav"
          flexDirection={{ base: 'row', md: 'column' }}
          gap="xs"
          padding="l"
          minWidth={{ md: 200 }}
          flexWrap="wrap"
        >
          {items.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(`${item.href}/`)
            return (
              <Link key={item.href} href={item.href}>
                <Box
                  paddingHorizontal="m"
                  paddingVertical="s"
                  borderRadius="m"
                  backgroundColor={active ? 'background-card' : undefined}
                >
                  <Text variant="body" color={active ? undefined : 'muted'}>
                    {item.label}
                  </Text>
                </Box>
              </Link>
            )
          })}
        </Box>
        <Box
          as="main"
          flexDirection="column"
          flexGrow={1}
          padding="l"
          rowGap="xl"
        >
          {children}
        </Box>
      </Box>
    </Box>
  )
}
