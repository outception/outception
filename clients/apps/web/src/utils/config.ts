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
  LOGIN_PATH: process.env.NEXT_PUBLIC_LOGIN_PATH || '/auth',
  GOOGLE_ANALYTICS_ID: process.env.NEXT_PUBLIC_GOOGLE_ANALYTICS_ID || undefined,
  SENTRY_DSN: process.env.NEXT_PUBLIC_SENTRY_DSN || undefined,
  POSTHOG_TOKEN: process.env.NEXT_PUBLIC_POSTHOG_TOKEN || '',
}

// Fail the build rather than ship localhost. FRONTEND_BASE_URL feeds
// metadataBase, every canonical, the sitemap, the JSON-LD url and the redirect
// host conditions - silently defaulting to 127.0.0.1 in production points every
// social preview and canonical at localhost, with nothing to warn you.
if (
  defaults.ENVIRONMENT === 'production' &&
  !process.env.NEXT_PUBLIC_FRONTEND_BASE_URL
) {
  throw new Error(
    'NEXT_PUBLIC_FRONTEND_BASE_URL must be set in production - it drives ' +
      'canonicals, the sitemap and every social preview URL.',
  )
}

export const CONFIG = {
  ...defaults,
}
