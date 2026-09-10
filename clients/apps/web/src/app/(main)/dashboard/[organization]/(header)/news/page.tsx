import { DashboardBody } from '@/components/Layout/DashboardLayout'
import { DashboardNewsWall } from '@/components/News/DashboardNewsWall'
import { metaTitle } from '@/utils/i18n'
import { Metadata } from 'next'

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: await metaTitle('news'),
  }
}

export default function Page() {
  return (
    <DashboardBody title={null}>
      <DashboardNewsWall />
    </DashboardBody>
  )
}
