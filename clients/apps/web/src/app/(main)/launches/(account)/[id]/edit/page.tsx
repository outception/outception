import { EditLaunch } from '@/components/Launches/EditLaunch'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'

export function generateMetadata(): Metadata {
  return { title: getTranslations().launches.submit.editTitle }
}

export default async function Page(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params
  return <EditLaunch id={id} />
}
