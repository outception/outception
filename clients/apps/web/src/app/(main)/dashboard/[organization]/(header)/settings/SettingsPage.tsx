'use client'

import { DashboardBody } from '@/components/Layout/DashboardLayout'
import OrganizationAccessTokensSettings from '@/components/Settings/OrganizationAccessTokensSettings'
import OrganizationNotificationSettings from '@/components/Settings/OrganizationNotificationSettings'
import { Section, SectionDescription } from '@/components/Settings/Section'
import { useUserOrganizationNotificationSettings } from '@/hooks/queries/user_organizations'
import { schemas } from '@polar-sh/client'

export default function ClientPage({
  organization: org,
}: {
  organization: schemas['Organization']
}) {
  const { data: userNotificationSettings } =
    useUserOrganizationNotificationSettings(org.id)

  return (
    <DashboardBody
      wrapperClassName="max-w-(--breakpoint-sm)!"
      title="Preferences"
    >
      <div className="flex flex-col gap-y-12">
        <Section id="account-notifications">
          <SectionDescription
            title="Your notifications"
            description="Choose which emails you receive as a member of this organization."
          />
          {userNotificationSettings && (
            <OrganizationNotificationSettings
              organization={org}
              userNotificationSettings={userNotificationSettings}
            />
          )}
        </Section>

        <Section id="developers">
          <SectionDescription
            title="Developers"
            description="Manage access tokens to authenticate with the API"
          />
          <OrganizationAccessTokensSettings organization={org} />
        </Section>
      </div>
    </DashboardBody>
  )
}
