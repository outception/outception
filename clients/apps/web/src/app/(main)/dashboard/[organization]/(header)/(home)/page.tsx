import { getServerSideAPI } from '@/utils/client/serverside'
import { getOrganizationBySlugOrNotFound } from '@/utils/organization'
import { metaTitle } from '@/utils/i18n'
import { Metadata } from 'next'
import DashboardPage from './DashboardPage'

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: await metaTitle('overview'), // " | Outception is added by the template"
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

  return <DashboardPage organization={organization} />
}
