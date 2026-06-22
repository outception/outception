'use client'

import { DashboardBody } from '@/components/Layout/DashboardLayout'
import { PromotionsDashboard } from '@/components/Promotions/PromotionsDashboard'
import { schemas } from '@polar-sh/client'

interface OverviewPageProps {
  organization: schemas['Organization']
}

export default function OverviewPage({
  organization: _organization,
}: OverviewPageProps) {
  return (
    <DashboardBody className="gap-y-8 pb-16 md:gap-y-16" title={null}>
      <PromotionsDashboard />
    </DashboardBody>
  )
}
