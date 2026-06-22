'use client'

import GetStartedButton from '@/components/Auth/GetStartedButton'
import { Button, Text } from '@polar-sh/orbit'
import { Box } from '@polar-sh/orbit/Box'
import Link from 'next/link'
import { PropsWithChildren } from 'react'

export default function LandingLayout({ children }: PropsWithChildren) {
  return (
    <Box
      flexDirection="column"
      minHeight="100vh"
      backgroundColor="background-primary"
    >
      <Box
        as="header"
        position="sticky"
        top={0}
        zIndex={30}
        alignItems="center"
        justifyContent="between"
        columnGap="m"
        paddingHorizontal="xl"
        paddingVertical="m"
        borderBottomWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
        backgroundColor="background-primary"
      >
        <Link href="/">
          <Text variant="heading-xs" as="span">
            Outception
          </Text>
        </Link>
        <Box alignItems="center" columnGap="s">
          <Link href="/dashboard/promotions">
            <Button variant="secondary" size="sm">
              My promotions
            </Button>
          </Link>
          <GetStartedButton text="Sign in" size="sm" />
        </Box>
      </Box>

      <Box as="main" flexDirection="column" flexGrow={1}>
        {children}
      </Box>

      <Box
        as="footer"
        alignItems="center"
        justifyContent="between"
        flexWrap="wrap"
        rowGap="s"
        paddingHorizontal="xl"
        paddingVertical="l"
        borderTopWidth={1}
        borderStyle="solid"
        borderColor="border-primary"
      >
        <Text variant="caption" color="muted">
          © Outception
        </Text>
        <Text variant="caption" color="muted">
          Live headlines · promote what matters
        </Text>
      </Box>
    </Box>
  )
}
