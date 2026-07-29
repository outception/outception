import AccessTokensSettings from '@/components/Settings/AccessTokenSettings'
import OAuthSettings from '@/components/Settings/OAuth/OAuthSettings'
import { Section, SectionDescription } from '@/components/Settings/Section'
import { metaTitle } from '@/utils/i18n'
import { Metadata } from 'next'

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: await metaTitle('developer'),
    description: 'Manage your developer settings',
  }
}

export default function Page() {
  return (
    <>
      <Section id="oauth">
        <SectionDescription
          title="OAuth Applications"
          description="Your configured OAuth Applications"
        />

        <OAuthSettings />
      </Section>
      <Section id="personal-access-tokens">
        <SectionDescription title="Personal Access Tokens" />
        <AccessTokensSettings />
      </Section>
    </>
  )
}
