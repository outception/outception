'use client'

import { LegalDialog } from '@/components/Legal/LegalDialog'
import { PrivacyContent } from '@/components/Legal/PrivacyContent'
import { TermsContent } from '@/components/Legal/TermsContent'
import {
  NewsColumnProvider,
  useNewsColumn,
} from '@/components/News/NewsColumnContext'
import { NewsNavTabs } from '@/components/News/NewsNavTabs'
import { useT } from '@/providers/locale'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import { PropsWithChildren } from 'react'

/**
 * The navbar. Sticky over the card view, which keeps its own top margin; over
 * the mosaic it goes FIXED, so it leaves the flow entirely and the first row
 * of tiles starts at the very top of the screen with the pill floating on it.
 * A sticky element still occupies its height, which is the band of empty
 * backdrop the mosaic used to begin below.
 *
 * Separate component because it reads the column context that the layout
 * itself provides.
 */
const LandingHeader = () => {
  const { view } = useNewsColumn()
  const floating = view === 'zoom'
  return (
    <Box
      as="header"
      position={floating ? 'fixed' : 'sticky'}
      top={0}
      width={floating ? '100%' : undefined}
      zIndex={30}
      flexDirection="column"
      alignItems="center"
      rowGap="m"
      paddingHorizontal="xl"
      // Flush with the top of the screen over the mosaic, so the bar reads as
      // hanging off the edge rather than floating a little below it.
      paddingVertical={floating ? 'none' : 'm'}
    >
      {/* The segmented pill on top, the red mark centered beneath - click it
          to toggle light/dark - matching the original navbar. Nothing on the
          sides. */}
      <NewsNavTabs />
    </Box>
  )
}

/**
 * The page footer. Hidden under the mosaic: the wall there has no end to
 * reach - the scroll turns back on itself at the last row - so a footer would
 * only ever be a promise of a bottom that never arrives.
 */
const LandingFooter = () => {
  const { view } = useNewsColumn()
  const t = useT()
  if (view === 'zoom') return null
  return (
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
