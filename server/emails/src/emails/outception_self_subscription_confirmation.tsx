import { Footer, Intro, Text, WrapperOutception } from '../components/foundation'
import type { schemas } from '../types'

export function OutceptionSelfSubscriptionConfirmation({
  email,
  product_name,
}: schemas['OutceptionSelfSubscriptionConfirmationProps']) {
  return (
    <WrapperOutception preview="We're happy to have you selling on Outception!">
      <Intro headline="Thanks for choosing Outception!">
        You're now subscribed to{' '}
        <Text as="span" weight="medium">
          {product_name}
        </Text>
        . Your invoice is attached for your records.
      </Intro>
      <Footer email={email} />
    </WrapperOutception>
  )
}

OutceptionSelfSubscriptionConfirmation.PreviewProps = {
  email: 'john@example.com',
  product_name: 'Outception Pro',
} satisfies schemas['OutceptionSelfSubscriptionConfirmationProps']

export default OutceptionSelfSubscriptionConfirmation
