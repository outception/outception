import LandingLayout from '@/components/Landing/LandingLayout'
import { LaunchArchive } from '@/components/Launches/LaunchArchive'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'

export function generateMetadata(): Metadata {
  const tr = getTranslations()
  return {
    title: tr.launches.archive.title,
    description: tr.launches.archive.intro,
  }
}

export default function Page() {
  return (
    <LandingLayout>
      <LaunchArchive />
    </LandingLayout>
  )
}
