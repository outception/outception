'use client'

import { Box } from '@outception-com/orbit/Box'
import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { NewsColumnProvider } from './NewsColumnContext'
import { NewsNavTabs } from './NewsNavTabs'
import { NewsWall } from './NewsWall'

const DashboardNewsWallInner = () => {
  // A live promotion links here with ?topic=<category> so the deck opens on the
  // card where that promotion is currently featured.
  const focusTopic = useSearchParams().get('topic') ?? undefined
  return (
    <NewsColumnProvider>
      <Box flexDirection="column" rowGap="l" paddingVertical="l">
        <Box alignItems="center" justifyContent="center">
          <NewsNavTabs />
        </Box>
        <NewsWall focusTopic={focusTopic} />
      </Box>
    </NewsColumnProvider>
  )
}

/** The public news wall embedded inside the dashboard shell (next to the
 * sidebar), so a signed-in user can browse the live feed — and see their own
 * promotions surface — without leaving the dashboard. Reuses the wall's column
 * context and its deck tabs ("Your deck" / "Trending" / More), minus the
 * landing page's full-screen header/footer chrome. */
export const DashboardNewsWall = () => {
  return (
    <Suspense>
      <DashboardNewsWallInner />
    </Suspense>
  )
}
