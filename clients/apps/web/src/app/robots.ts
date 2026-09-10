import { CONFIG } from '@/utils/config'
import { MetadataRoute } from 'next'

// /handbook is login-gated, so crawlers only get a redirect - saying so
// saves the crawl budget. The sitemap follows the deployment rather than
// hardcoding production, or preview deploys advertise the live sitemap.
const DISALLOW = ['/dashboard/', '/auth/', '/verify-email/', '/handbook/']

// The crawlers that feed AI answer engines, allowed by NAME: a bare wildcard
// is technically enough, but several readiness graders (and some of the bots
// themselves) treat an explicit entry as the real signal of consent.
const AI_CRAWLERS = [
  'GPTBot',
  'ChatGPT-User',
  'OAI-SearchBot',
  'ClaudeBot',
  'anthropic-ai',
  'PerplexityBot',
  'Google-Extended',
  'Applebot-Extended',
  'CCBot',
  'meta-externalagent',
]

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: '*', allow: '/', disallow: DISALLOW },
      ...AI_CRAWLERS.map((userAgent) => ({
        userAgent,
        allow: '/',
        disallow: DISALLOW,
      })),
    ],
    sitemap: `${CONFIG.FRONTEND_BASE_URL}/sitemap.xml`,
  }
}
