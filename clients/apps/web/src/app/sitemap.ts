import { LANDING_PAGES } from '@/lib/seo/landingPages'
import { CONFIG } from '@/utils/config'
import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const base = CONFIG.FRONTEND_BASE_URL.replace(/\/$/, '')
  const now = new Date()

  return [
    {
      url: CONFIG.FRONTEND_BASE_URL,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 1,
    },
    {
      url: `${base}/hand`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.8,
    },
    {
      url: `${base}/launches`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.6,
    },
    ...LANDING_PAGES.map((p) => ({
      url: `${base}/${p.slug}`,
      lastModified: now,
      changeFrequency: 'monthly' as const,
      priority: 0.8,
    })),
    ...['privacy', 'terms'].map((slug) => ({
      url: `${base}/${slug}`,
      lastModified: now,
      changeFrequency: 'yearly' as const,
      priority: 0.3,
    })),
  ]
}
