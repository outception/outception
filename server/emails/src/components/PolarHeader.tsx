import { Section } from 'react-email'
import { BRAND_NAME } from './brand'
import { Text } from './foundation/Text'

const Header = () => (
  <Section>
    <Text variant="lead" weight="bold" as="span" noMargin>
      {BRAND_NAME}
    </Text>
  </Section>
)

export default Header
