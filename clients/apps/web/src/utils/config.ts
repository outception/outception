const defaults = {
  ENVIRONMENT:
    process.env.NEXT_PUBLIC_ENVIRONMENT ||
    process.env.VERCEL_ENV ||
    process.env.NEXT_PUBLIC_VERCEL_ENV ||
    'development',
  FRONTEND_BASE_URL:
    process.env.NEXT_PUBLIC_FRONTEND_BASE_URL || 'http://127.0.0.1:3000',
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000',
  AUTH_COOKIE_KEY:
    process.env.OUTCEPTION_AUTH_COOKIE_KEY || 'outception_session',
  AUTH_MCP_COOKIE_KEY:
    process.env.OUTCEPTION_AUTH_MCP_COOKIE_KEY || 'outception_mcp_session',
  LOGIN_PATH: process.env.NEXT_PUBLIC_LOGIN_PATH || '/auth',
  GOOGLE_ANALYTICS_ID: process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_ID || undefined,
  GITHUB_APP_NAMESPACE:
    process.env.NEXT_PUBLIC_GITHUB_APP_NAMESPACE || 'outception-com',
  SENTRY_DSN: process.env.NEXT_PUBLIC_SENTRY_DSN || undefined,
  POSTHOG_TOKEN: process.env.NEXT_PUBLIC_POSTHOG_TOKEN || '',
}

export const CONFIG = {
  ...defaults,
  GITHUB_INSTALLATION_URL: `https://github.com/apps/${defaults.GITHUB_APP_NAMESPACE}/installations/new`,
}
