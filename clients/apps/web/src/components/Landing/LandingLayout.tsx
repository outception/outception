'use client'

import { CreditsDrawer } from '@/components/Landing/CreditsDrawer'
import { TellUsSheet } from '@/components/Landing/TellUsSheet'
import { LegalDialog } from '@/components/Legal/LegalDialog'
import { PrivacyContent } from '@/components/Legal/PrivacyContent'
import { TermsContent } from '@/components/Legal/TermsContent'
import { NewsColumnProvider } from '@/components/News/NewsColumnContext'
import { NewsNavTabs } from '@/components/News/NewsNavTabs'
import { useT } from '@/providers/translate'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import { PropsWithChildren } from 'react'

/** The navbar. Sticky over the card view, which keeps its own top margin. */
const LandingHeader = () => {
  return (
    <Box
      as="header"
      position="sticky"
      top={0}
      zIndex={30}
      flexDirection="column"
      alignItems="center"
      rowGap="m"
      paddingHorizontal="xl"
      // Flush with the top of the screen, so the bar reads as hanging off the
      // edge rather than floating a little below it. The space it keeps is
      // UNDER it.
      paddingTop="none"
      paddingBottom="m"
    >
      {/* The segmented pill on top, the red mark centered beneath - click it
          to toggle light/dark - matching the original navbar. Nothing on the
          sides. */}
      <NewsNavTabs />
    </Box>
  )
}

const Dot = () => (
  <Text variant="caption" color="disabled" aria-hidden>
    ·
  </Text>
)

/** The page footer: the trust line, then the small print. */
const LandingFooter = () => {
  const t = useT()
  return (
    <Box
      as="footer"
      flexDirection="column"
      alignItems="center"
      rowGap="s"
      paddingHorizontal="xl"
      paddingVertical="l"
    >
      <Box textAlign="center" maxWidth={640}>
        <Text variant="caption" color="muted" as="p">
          {t('news.trust.line')}
        </Text>
      </Box>
      <Box
        alignItems="center"
        justifyContent="center"
        flexWrap="wrap"
        rowGap="s"
        columnGap="s"
      >
        <Text variant="caption" color="muted">
          {t('news.footer')}
        </Text>
        <Dot />
        <CreditsDrawer />
        <Dot />
        <TellUsSheet />
        <Text variant="caption" color="disabled" aria-hidden>
          ·
        </Text>
        <LegalDialog label={t('news.privacy')} title={t('legal.privacy.title')}>
          <PrivacyContent />
        </LegalDialog>
        <Text variant="caption" color="disabled" aria-hidden>
          ·
        </Text>
        <LegalDialog label={t('news.terms')} title={t('legal.terms.title')}>
          <TermsContent />
        </LegalDialog>
      </Box>
    </Box>
  )
}

export default function LandingLayout({ children }: PropsWithChildren) {
  return (
    <NewsColumnProvider>
      <Box flexDirection="column" minHeight="100vh">
        {/* Reserve the iOS status-bar area so content clears the notch, while
            the fixed PaperBackground still fills behind it (plain div - env()
            isn't a Box token). */}
        <div
          aria-hidden
          style={{ height: 'env(safe-area-inset-top)', flexShrink: 0 }}
        />
        <LandingHeader />

        <Box as="main" flexDirection="column" flexGrow={1}>
          {children}
        </Box>

        <LandingFooter />
        {/* Clear the iOS home indicator, same idea as the top spacer. */}
        <div
          aria-hidden
          style={{ height: 'env(safe-area-inset-bottom)', flexShrink: 0 }}
        />
      </Box>
    </NewsColumnProvider>
  )
}
