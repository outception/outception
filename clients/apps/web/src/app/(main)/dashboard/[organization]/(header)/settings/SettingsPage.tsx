'use client'

import { DashboardBody } from '@/components/Layout/DashboardLayout'
import OrganizationAccessTokensSettings from '@/components/Settings/OrganizationAccessTokensSettings'
import { Section, SectionDescription } from '@/components/Settings/Section'
import { schemas } from '@outception-com/client'

export default function ClientPage({
  organization: org,
}: {
  organization: schemas['Organization']
}) {
  return (
    <DashboardBody
      wrapperClassName="max-w-(--breakpoint-sm)!"
      title="Preferences"
    >
      <div className="flex flex-col gap-y-12">
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
