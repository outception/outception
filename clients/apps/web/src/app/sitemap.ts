import { crawlerSlugs } from '@/lib/seo/crawler'
import { LANDING_PAGES } from '@/lib/seo/landingPages'
import { CONFIG } from '@/utils/config'
import { MetadataRoute } from 'next'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = CONFIG.FRONTEND_BASE_URL.replace(/\/$/, '')
  const now = new Date()
  // The country, city and Starter pages: the crawler's doorways to the wall.
  const crawler = await crawlerSlugs()

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
    {
      url: `${base}/changelog`,
      lastModified: now,
      changeFrequency: 'weekly' as const,
      priority: 0.4,
    },
    ...crawler.map((slug) => ({
      url: `${base}/${slug}`,
      lastModified: now,
      changeFrequency: 'hourly' as const,
      priority: 0.7,
    })),
    ...['privacy', 'terms'].map((slug) => ({
      url: `${base}/${slug}`,
      lastModified: now,
      changeFrequency: 'yearly' as const,
      priority: 0.3,
    })),
  ]
}
