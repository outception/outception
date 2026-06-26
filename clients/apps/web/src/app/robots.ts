import { CONFIG } from '@/utils/config'
import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  if (CONFIG.IS_SANDBOX) {
    return {
      rules: {
        userAgent: '*',
        disallow: '/',
      },
    }
  }

  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/dashboard/', '/auth/', '/verify-email/'],
    },
    sitemap: 'https://outception.com/sitemap.xml',
  }
}
