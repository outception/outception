'use client'

import { DashboardBody } from '@/components/Layout/DashboardLayout'
import { useT } from '@/providers/locale'
import OrganizationAccessTokensSettings from '@/components/Settings/OrganizationAccessTokensSettings'
import { Section, SectionDescription } from '@/components/Settings/Section'
import { schemas } from '@outception-com/client'

export default function ClientPage({
  organization: org,
}: {
  organization: schemas['Organization']
}) {
  const t = useT()
  return (
    <DashboardBody
      wrapperClassName="max-w-(--breakpoint-sm)!"
      title={t('settings.preferences')}
    >
      <div className="flex flex-col gap-y-12">
        <Section id="developers">
          <SectionDescription
            title={t('settings.developers')}
            description={t('settings.developersDesc')}
          />
          <OrganizationAccessTokensSettings organization={org} />
        </Section>
      </div>
    </DashboardBody>
  )
}
