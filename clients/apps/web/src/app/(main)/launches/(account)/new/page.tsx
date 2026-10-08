import { SubmitLaunchForm } from '@/components/Launches/SubmitLaunchForm'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'

export function generateMetadata(): Metadata {
  return { title: getTranslations().launches.submit.title }
}

export default function Page() {
  return <SubmitLaunchForm />
}
