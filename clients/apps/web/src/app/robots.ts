import { CONFIG } from '@/utils/config'
import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      // /handbook is login-gated, so crawlers only get a redirect — saying so
      // saves the crawl budget. The sitemap follows the deployment rather than
      // hardcoding production, or preview deploys advertise the live sitemap.
      disallow: ['/dashboard/', '/auth/', '/verify-email/', '/handbook/'],
    },
    sitemap: `${CONFIG.FRONTEND_BASE_URL}/sitemap.xml`,
  }
}
