import LandingLayout from '@/components/Landing/LandingLayout'
import { ProductPage } from '@/components/Launches/ProductPage'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'

export function generateMetadata(): Metadata {
  return { title: getTranslations().launches.archive.title }
}

/** One product's page: public once listed, the submitter's before that. */
export default async function Page(props: { params: Promise<{ id: string }> }) {
  const { id } = await props.params
  return (
    <LandingLayout>
      <ProductPage id={id} />
    </LandingLayout>
  )
}
