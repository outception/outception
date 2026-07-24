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
  // Google AdSense. CLIENT is the publisher id ("ca-pub-…"); SLOT_WALL is the
  // ad-unit slot id for the news wall. Both public. Unset = ads off (nothing
  // loads), so the site works before AdSense approval.
  ADSENSE_CLIENT: process.env.NEXT_PUBLIC_ADSENSE_CLIENT || undefined,
  ADSENSE_SLOT_WALL: process.env.NEXT_PUBLIC_ADSENSE_SLOT_WALL || undefined,
}

export const CONFIG = {
  ...defaults,
}
