import AuthenticationSettings from '@/components/Settings/AuthenticationSettings'
import PersonalInformationSettings from '@/components/Settings/PersonalInformationSettings'
import { Section, SectionDescription } from '@/components/Settings/Section'
import TwoFactorSettings from '@/components/Settings/TwoFactorSettings'
import UserDeleteSettings from '@/components/Settings/UserDeleteSettings'
import { metaTitle, resolveLocale } from '@/utils/i18n'
import { getTranslations } from '@outception-com/i18n'
import { Metadata } from 'next'

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: await metaTitle('preferences'),
    description: 'Manage your account preferences',
  }
}

export default async function Page() {
  const tr = getTranslations(await resolveLocale())
  const s = tr.account.sections
  return (
    <>
      <Section>
        <SectionDescription title={s.personal} />
        <PersonalInformationSettings />
      </Section>
      <Section>
        <SectionDescription title={s.auth} />
        <AuthenticationSettings />
      </Section>
      <Section>
        <SectionDescription title={s.twoFactor} />
        <TwoFactorSettings />
      </Section>
      <Section>
        <SectionDescription title={s.danger} description={s.dangerDesc} />
        <UserDeleteSettings />
      </Section>
    </>
  )
}
