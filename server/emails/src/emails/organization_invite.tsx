import { BRAND_NAME } from '../components/brand'
import {
  Button,
  Footer,
  Intro,
  Text,
  WrapperPolar,
} from '../components/foundation'
import type { schemas } from '../types'

export function OrganizationInvite({
  email,
  organization_name,
  inviter_email,
  invite_url,
}: schemas['OrganizationInviteProps']) {
  return (
    <WrapperPolar
      preview={`You've been added to ${organization_name} on ${BRAND_NAME}`}
    >
      <Intro>
        {inviter_email} has added you to{' '}
        <Text as="span" weight="bold">
          {organization_name}
        </Text>{' '}
        on {BRAND_NAME}.
      </Intro>
      <Text>
        As a member of {organization_name} you're now able to manage{' '}
        {organization_name}'s products, customers, and subscriptions on{' '}
        {BRAND_NAME}.
      </Text>
      <Button href={invite_url}>Go to the {BRAND_NAME} dashboard</Button>
      <Footer email={email} />
    </WrapperPolar>
  )
}

OrganizationInvite.PreviewProps = {
  email: 'john@example.com',
  organization_name: 'Acme Inc.',
  inviter_email: 'admin@acme.com',
  invite_url: 'https://polar.sh/dashboard/acme-inc',
}

export default OrganizationInvite
