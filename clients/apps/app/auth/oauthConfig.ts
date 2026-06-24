// OAuth2 (PKCE) config for the mobile app. Everything is env-driven so wiring
// the app to a deployment is just setting env vars — no code edits.
//
// To get a CLIENT_ID:
//   1. Create an OAuth app at <web>/dashboard/account/developer
//   2. Choose "Public Client" and grant it the `scopes` below
//   3. Set the Redirect URI to "polar://oauth/callback"
//
// Then set, for your environment:
//   EXPO_PUBLIC_POLAR_SERVER_URL   — the API base (e.g. https://api.yourdomain)
//   EXPO_PUBLIC_POLAR_WEB_URL      — the web base (e.g. https://app.yourdomain)
//   EXPO_PUBLIC_OAUTH_CLIENT_ID    — the public client id from step 2

const API_URL =
  process.env.EXPO_PUBLIC_POLAR_SERVER_URL ?? 'http://127.0.0.1:8000'
const WEB_URL = process.env.EXPO_PUBLIC_POLAR_WEB_URL ?? 'http://127.0.0.1:3000'

export const CLIENT_ID = process.env.EXPO_PUBLIC_OAUTH_CLIENT_ID ?? ''

export const discovery = {
  authorizationEndpoint: `${WEB_URL}/oauth2/authorize`,
  tokenEndpoint: `${API_URL}/v1/oauth2/token`,
  registrationEndpoint: `${API_URL}/v1/oauth2/register`,
  revocationEndpoint: `${API_URL}/v1/oauth2/revoke`,
}

export const scopes = [
  'openid',
  'profile',
  'email',
  'user:read',
  'user:write',
  'organizations:read',
  'organizations:write',
  'members:read',
  'members:write',
  'organization_access_tokens:read',
  'organization_access_tokens:write',
  'promotions:read',
  'promotions:write',
]
