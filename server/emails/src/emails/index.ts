import { EmailUpdate } from './email_update'
import { LoginCode } from './login_code'
import { OAuth2LeakedClient } from './oauth2_leaked_client'
import { OAuth2LeakedToken } from './oauth2_leaked_token'
import { OrganizationAccessTokenLeaked } from './organization_access_token_leaked'
import { OrganizationInvite } from './organization_invite'
import { PersonalAccessTokenLeaked } from './personal_access_token_leaked'

const TEMPLATES: Record<string, React.FC<never>> = {
  login_code: LoginCode,
  email_update: EmailUpdate,
  oauth2_leaked_client: OAuth2LeakedClient,
  oauth2_leaked_token: OAuth2LeakedToken,
  organization_access_token_leaked: OrganizationAccessTokenLeaked,
  organization_invite: OrganizationInvite,
  personal_access_token_leaked: PersonalAccessTokenLeaked,
}

export default TEMPLATES
