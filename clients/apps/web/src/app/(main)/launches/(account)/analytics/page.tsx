import { AnalyticsPage } from '@/components/Analytics/AnalyticsPage'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'

export function generateMetadata(): Metadata {
  return { title: getTranslations().launches.analytics.title }
}

export default function Page() {
  return <AnalyticsPage />
}
