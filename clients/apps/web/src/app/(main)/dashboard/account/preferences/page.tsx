import AuthenticationSettings from '@/components/Settings/AuthenticationSettings'
import GeneralSettings from '@/components/Settings/GeneralSettings'
import PersonalInformationSettings from '@/components/Settings/PersonalInformationSettings'
import { PromotionEmailSettings } from '@/components/Settings/PromotionEmailSettings'
import { Section, SectionDescription } from '@/components/Settings/Section'
import TwoFactorSettings from '@/components/Settings/TwoFactorSettings'
import UserDeleteSettings from '@/components/Settings/UserDeleteSettings'
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Preferences',
  description: 'Manage your account preferences',
}

export default function Page() {
  return (
    <>
      <Section>
        <SectionDescription title="Personal Information" />
        <PersonalInformationSettings />
      </Section>
      <Section>
        <SectionDescription title="General" />
        <GeneralSettings />
      </Section>
      <Section>
        <SectionDescription title="Authentication Methods" />
        <AuthenticationSettings />
      </Section>
      <Section>
        <SectionDescription title="Two-Factor Authentication" />
        <TwoFactorSettings />
      </Section>
      <Section>
        <SectionDescription
          title="Promotion Emails"
          description="Control the emails you receive about your promotions."
        />
        <PromotionEmailSettings />
      </Section>
      <Section>
        <SectionDescription
          title="Danger Zone"
          description="Irreversible actions for your account"
        />
        <UserDeleteSettings />
      </Section>
    </>
  )
}
