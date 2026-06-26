import {
  Button,
  Footer,
  Intro,
  Text,
  WrapperOutception,
} from '../components/foundation'
import type { schemas } from '../types'

export function OutceptionSelfStartupProgramWelcome({
  email,
  organization_name,
  billing_url,
}: schemas['OutceptionSelfStartupProgramWelcomeProps']) {
  return (
    <WrapperOutception
      preview={`${organization_name} is in the Outception Startup Program. 12 months free on Scale.`}
    >
      <Intro headline="Welcome to the Outception Startup Program">
        We&apos;re excited to have{' '}
        <Text as="span" weight="bold">
          {organization_name}
        </Text>{' '}
        join the next generation of startups building with Outception. You get the
        Scale plan{' '}
        <Text as="span" weight="bold">
          free for 12 months
        </Text>
        .
      </Intro>
      <Text>
        To claim it, head to your billing settings and switch to the Scale plan.
        The 100% discount is available on your account and will apply
        automatically at checkout, no code needed.
      </Text>
      <Button href={billing_url}>Go to billing</Button>
      <Text>
        The discount applies for 12 months from the day you upgrade, then your
        plan rolls over to the standard Scale pricing. You can manage or cancel
        anytime from the same billing page.
      </Text>
      <Footer email={email} />
    </WrapperOutception>
  )
}

OutceptionSelfStartupProgramWelcome.PreviewProps = {
  email: 'founder@acme.ai',
  organization_name: 'Acme AI',
  billing_url: 'https://outception.com/dashboard/acme/settings/billing/change-plan',
} satisfies schemas['OutceptionSelfStartupProgramWelcomeProps']

export default OutceptionSelfStartupProgramWelcome
