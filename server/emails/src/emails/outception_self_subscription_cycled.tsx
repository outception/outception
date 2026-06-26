import { Footer, Intro, Text, WrapperOutception } from '../components/foundation'
import type { schemas } from '../types'

export function OutceptionSelfSubscriptionCycled({
  email,
  product_name,
}: schemas['OutceptionSelfSubscriptionCycledProps']) {
  return (
    <WrapperOutception preview={`Your ${product_name} subscription renewed`}>
      <Intro headline={`${product_name} renewed`}>
        Your{' '}
        <Text as="span" weight="medium">
          {product_name}
        </Text>{' '}
        subscription renewed for another cycle. The latest invoice is attached.
      </Intro>
      <Footer email={email} />
    </WrapperOutception>
  )
}

OutceptionSelfSubscriptionCycled.PreviewProps = {
  email: 'john@example.com',
  product_name: 'Outception Pro',
} satisfies schemas['OutceptionSelfSubscriptionCycledProps']

export default OutceptionSelfSubscriptionCycled
