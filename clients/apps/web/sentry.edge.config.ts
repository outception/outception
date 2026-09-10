// Edge-runtime Sentry init (middleware, edge routes). Also loaded locally.

import { CONFIG } from '@/utils/config'
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: CONFIG.SENTRY_DSN,
  environment: CONFIG.ENVIRONMENT,

  // 10% of requests is enough for latency trends without eating quota.
  tracesSampleRate: 0.1,
  debug: false,
})
