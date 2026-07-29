// Browser-side Sentry init.

import { CONFIG } from '@/utils/config'
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: CONFIG.SENTRY_DSN,
  environment: CONFIG.ENVIRONMENT,

  integrations: [
    Sentry.httpClientIntegration(),
    Sentry.browserTracingIntegration(),
  ],

  // 10% of page loads is enough for latency trends without eating quota.
  tracesSampleRate: 0.1,

  // Propagate trace headers to our API only, never to third-party hosts.
  tracePropagationTargets: [/^https:\/\/api\.outception\.sh/],

  // Session replay is off: it records reader screens we have no use for.
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,

  debug: false,

  ignoreErrors: [
    /WeakMap key undefined/i,
    /NetworkError/i,
    /AbortError/i,
    /HTTP Client Error with status code: 5\d\d/i,
    /Exceeded storage quota/i,
    /QuotaExceededError/i,
    /ResizeObserver loop/i,
    /Non-Error promise rejection/i,
  ],

  denyUrls: [/extensions\//i, /^chrome:\/\//i, /^moz-extension:\/\//i],

  beforeSend: (event) => {
    // Do not flag PostHog errors
    if (
      event.request?.url?.includes('/ingest/flags') ||
      event.request?.url?.includes('/ingest/batch')
    ) {
      return null
    }

    // Group fetch errors by page URL so they don't all pile into one issue
    const message = event.exception?.values?.[0]?.value ?? ''
    if (/Failed to fetch|Load failed/i.test(message)) {
      const page =
        event.request?.url?.replace(/https?:\/\/[^/]+/, '') ?? 'unknown'
      const normalized = page.replace(
        /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi,
        ':id',
      )
      event.fingerprint = ['fetch-error', normalized]
    }

    return event
  },
})

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart
