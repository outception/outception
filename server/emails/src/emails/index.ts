import { EmailUpdate } from './email_update'
import { LoginCode } from './login_code'
import { OAuth2LeakedClient } from './oauth2_leaked_client'
import { OAuth2LeakedToken } from './oauth2_leaked_token'
import { OrderConfirmation } from './order_confirmation'
import { OrganizationAccessTokenLeaked } from './organization_access_token_leaked'
import { OrganizationInvite } from './organization_invite'
import { PersonalAccessTokenLeaked } from './personal_access_token_leaked'
import { SubscriptionCancellation } from './subscription_cancellation'
import { SubscriptionConfirmation } from './subscription_confirmation'
import { SubscriptionCycled } from './subscription_cycled'
import { SubscriptionCycledAfterTrial } from './subscription_cycled_after_trial'
import { SubscriptionPastDue } from './subscription_past_due'
import { SubscriptionRenewalReminder } from './subscription_renewal_reminder'
import { SubscriptionRevoked } from './subscription_revoked'
import { SubscriptionTrialConversionReminder } from './subscription_trial_conversion_reminder'
import { SubscriptionUncanceled } from './subscription_uncanceled'
import { SubscriptionUpdated } from './subscription_updated'

const TEMPLATES: Record<string, React.FC<never>> = {
  login_code: LoginCode,
  email_update: EmailUpdate,
  oauth2_leaked_client: OAuth2LeakedClient,
  oauth2_leaked_token: OAuth2LeakedToken,
  order_confirmation: OrderConfirmation,
  organization_access_token_leaked: OrganizationAccessTokenLeaked,
  organization_invite: OrganizationInvite,
  personal_access_token_leaked: PersonalAccessTokenLeaked,
  subscription_cancellation: SubscriptionCancellation,
  subscription_confirmation: SubscriptionConfirmation,
  subscription_cycled: SubscriptionCycled,
  subscription_cycled_after_trial: SubscriptionCycledAfterTrial,
  subscription_past_due: SubscriptionPastDue,
  subscription_renewal_reminder: SubscriptionRenewalReminder,
  subscription_revoked: SubscriptionRevoked,
  subscription_trial_conversion_reminder: SubscriptionTrialConversionReminder,
  subscription_uncanceled: SubscriptionUncanceled,
  subscription_updated: SubscriptionUpdated,
}

export default TEMPLATES
