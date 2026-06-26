import {
  Button,
  Footer,
  Intro,
  Text,
  WrapperOutception,
} from '../components/foundation'
import type { schemas } from '../types'

export function SupportCaseOrganizationNewMessage({
  email,
  organization_name,
  case_label,
  url,
}: schemas['SupportCaseOrganizationNewMessageProps']) {
  return (
    <WrapperOutception preview={`Update on your ${organization_name} ${case_label}`}>
      <Intro>
        There's an update on your {case_label} for{' '}
        <Text as="span" weight="bold">
          {organization_name}
        </Text>
        .
      </Intro>
      <Button href={url}>View your {case_label}</Button>
      <Text variant="caption">
        This inbox isn't monitored — please don't reply to this email. To
        respond, open your {case_label} using the button above.
      </Text>
      <Footer email={email} />
    </WrapperOutception>
  )
}

SupportCaseOrganizationNewMessage.PreviewProps = {
  email: 'merchant@example.com',
  organization_name: 'Acme Inc.',
  case_label: 'appeal',
  url: 'https://outception.com/dashboard/acme-inc/finance/account',
}

export default SupportCaseOrganizationNewMessage
