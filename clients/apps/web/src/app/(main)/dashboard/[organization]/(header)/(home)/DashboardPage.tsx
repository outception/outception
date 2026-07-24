'use client'

import { DashboardBody } from '@/components/Layout/DashboardLayout'
import { schemas } from '@outception-com/client'
import { Box } from '@outception-com/orbit/Box'
import { Text } from '@outception-com/orbit'

interface OverviewPageProps {
  organization: schemas['Organization']
}

export default function OverviewPage({
  organization: _organization,
}: OverviewPageProps) {
  return (
    <DashboardBody className="gap-y-8 pb-16 md:gap-y-16" title={null}>
      <Box flexDirection="column" rowGap="s" paddingVertical="2xl">
        <Text variant="heading-m" as="h1">
          Welcome to Outception
        </Text>
        <Text color="muted">
          Open the News Wall from the sidebar to browse the live feed.
        </Text>
      </Box>
    </DashboardBody>
  )
}
