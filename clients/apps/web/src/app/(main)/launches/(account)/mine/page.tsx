import { MyLaunches } from '@/components/Launches/MyLaunches'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'

export function generateMetadata(): Metadata {
  return { title: getTranslations().launches.mine.title }
}

export default function Page() {
  return <MyLaunches />
}
