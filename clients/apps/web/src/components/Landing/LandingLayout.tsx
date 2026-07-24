'use client'

import { OutceptionLogotype } from '@/components/Layout/Public/OutceptionLogotype'
import { NewsColumnProvider } from '@/components/News/NewsColumnContext'
import { NewsNavTabs } from '@/components/News/NewsNavTabs'
import { useT } from '@/providers/locale'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import Link from 'next/link'
import { PropsWithChildren } from 'react'

export default function LandingLayout({ children }: PropsWithChildren) {
  const t = useT()
  return (
    <NewsColumnProvider>
      <Box flexDirection="column" minHeight="100vh">
        {/* Reserve the iOS status-bar area so content clears the notch, while
            the fixed PaperBackground still fills behind it (plain div — env()
            isn't a Box token). */}
        <div
          aria-hidden
          style={{ height: 'env(safe-area-inset-top)', flexShrink: 0 }}
        />
        <Box
          as="header"
          position="sticky"
          top={0}
          zIndex={30}
          flexDirection="column"
          alignItems="center"
          rowGap="m"
          paddingHorizontal="xl"
          paddingVertical="m"
        >
          {/* The segmented pill on top, the red mark centered beneath — click it
              to toggle light/dark — matching the original navbar. Nothing on the
              sides. */}
          <NewsNavTabs />
          {/* Dropped down on mobile so it clears the tabs / status bar. The
              mark sits between short hairlines, like a section ornament.
              (Plain divs: Box has no token for the newsprint ink hairline —
              the AGENTS.md escape hatch for one-offs Orbit can't express.) */}
          <Box
            marginTop={{ base: '2xl', md: 'none' }}
            alignItems="center"
            columnGap="m"
          >
            <div aria-hidden className="rule-hairline w-12" />
            <OutceptionLogotype href="/" togglesTheme size={32} />
            <div aria-hidden className="rule-hairline w-12" />
          </Box>
        </Box>

        <Box as="main" flexDirection="column" flexGrow={1}>
          {children}
        </Box>

        <Box
          as="footer"
          alignItems="center"
          justifyContent="center"
          flexWrap="wrap"
          rowGap="s"
          columnGap="s"
          paddingHorizontal="xl"
          paddingVertical="l"
        >
          <Text variant="caption" color="muted">
            {t('news.footer')}
          </Text>
          <Text variant="caption" color="disabled" aria-hidden>
            ·
          </Text>
          <Link href="/privacy" style={{ textDecoration: 'none' }}>
            <Text variant="caption" color="muted">
              {t('news.privacy')}
            </Text>
          </Link>
          <Text variant="caption" color="disabled" aria-hidden>
            ·
          </Text>
          <Link href="/terms" style={{ textDecoration: 'none' }}>
            <Text variant="caption" color="muted">
              {t('news.terms')}
            </Text>
          </Link>
        </Box>
        {/* Clear the iOS home indicator, same idea as the top spacer. */}
        <div
          aria-hidden
          style={{ height: 'env(safe-area-inset-bottom)', flexShrink: 0 }}
        />
      </Box>
    </NewsColumnProvider>
  )
}
