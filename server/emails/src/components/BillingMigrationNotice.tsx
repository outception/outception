import InfoBox from './InfoBox'
import { Text } from './foundation'

export function BillingMigrationNotice({
  organizationName,
  previousBillingProvider,
}: {
  organizationName: string
  previousBillingProvider: string
}) {
  return (
    <InfoBox title="Billing has moved to Outception">
      <Text>
        {organizationName} has migrated your subscription from{' '}
        {previousBillingProvider} to Outception. {previousBillingProvider} will no
        longer bill you.
      </Text>
    </InfoBox>
  )
}

export default BillingMigrationNotice
