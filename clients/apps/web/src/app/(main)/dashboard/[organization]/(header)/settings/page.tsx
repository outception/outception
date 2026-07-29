import { getServerSideAPI } from '@/utils/client/serverside'
import { getOrganizationBySlugOrNotFound } from '@/utils/organization'
import { metaTitle } from '@/utils/i18n'
import { Metadata } from 'next'
import SettingsPage from './SettingsPage'

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: await metaTitle('settings'), // " | Outception is added by the template"
  }
}

export default async function Page(props: {
  params: Promise<{ organization: string }>
}) {
  const params = await props.params
  const api = await getServerSideAPI()
  const organization = await getOrganizationBySlugOrNotFound(
    api,
    params.organization,
  )

  return <SettingsPage organization={organization} />
}
