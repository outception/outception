import { CONFIG } from '@/utils/config'
import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  // Don't generate sitemap for sandbox environment
  if (CONFIG.IS_SANDBOX) {
    return []
  }

  return [
    {
      url: CONFIG.FRONTEND_BASE_URL,
      lastModified: new Date(),
      changeFrequency: 'daily',
      priority: 1,
    },
  ]
}
