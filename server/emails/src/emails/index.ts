import { LoginCode } from './login_code'
import { OAuth2LeakedClient } from './oauth2_leaked_client'
import { OAuth2LeakedToken } from './oauth2_leaked_token'

const TEMPLATES: Record<string, React.FC<never>> = {
  login_code: LoginCode,
  oauth2_leaked_client: OAuth2LeakedClient,
  oauth2_leaked_token: OAuth2LeakedToken,
}

export default TEMPLATES
