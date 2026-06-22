import { DashboardBody } from '@/components/Layout/DashboardLayout'
import { PromotionsDashboard } from '@/components/Promotions/PromotionsDashboard'
import { Metadata } from 'next'

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: 'Promotions',
  }
}

export default function Page() {
  return (
    <DashboardBody title={null}>
      <PromotionsDashboard />
    </DashboardBody>
  )
}
