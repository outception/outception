import { DashboardBody } from '@/components/Layout/DashboardLayout'
import { PromotionsDashboard } from '@/components/Promotions/PromotionsDashboard'
import { Metadata } from 'next'

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: 'Promotions',
  }
}

export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ compose?: string }>
}) {
  const { compose } = await searchParams
  return (
    <DashboardBody title={null}>
      <PromotionsDashboard defaultCompose={compose === '1'} />
    </DashboardBody>
  )
}
