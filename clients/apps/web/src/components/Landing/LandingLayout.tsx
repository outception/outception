'use client'

import { OutceptionLogotype } from '@/components/Layout/Public/OutceptionLogotype'
import { NewsColumnProvider } from '@/components/News/NewsColumnContext'
import { NewsNavTabs } from '@/components/News/NewsNavTabs'
import { useT } from '@/providers/locale'
import { Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import { PropsWithChildren } from 'react'

export default function LandingLayout({ children }: PropsWithChildren) {
  const t = useT()
  return (
    <NewsColumnProvider>
      <Box flexDirection="column" minHeight="100vh">
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
          {/* Dropped down on mobile so it clears the tabs / status bar. */}
          <Box marginTop={{ base: '2xl', md: 'none' }}>
            <OutceptionLogotype href="/" togglesTheme size={32} />
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
          paddingHorizontal="xl"
          paddingVertical="l"
        >
          <Text variant="caption" color="muted">
            {t('news.footer')}
          </Text>
        </Box>
      </Box>
    </NewsColumnProvider>
  )
}
