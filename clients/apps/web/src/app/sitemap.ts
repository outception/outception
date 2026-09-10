import { basePathForSet, listSlugs } from '@/lib/docs/content'
import { LANDING_PAGES } from '@/lib/seo/landingPages'
import { CONFIG } from '@/utils/config'
import { MetadataRoute } from 'next'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = CONFIG.FRONTEND_BASE_URL.replace(/\/$/, '')
  const now = new Date()

  // Only the public docs set is indexed; the handbook is auth-gated.
  const docsSlugs = await listSlugs('docs')
  const docEntries: MetadataRoute.Sitemap = docsSlugs.map((slug) => ({
    url: `${base}${basePathForSet('docs')}/${slug.join('/')}`,
    lastModified: now,
    changeFrequency: 'weekly',
    priority: 0.7,
  }))

  return [
    {
      url: CONFIG.FRONTEND_BASE_URL,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 1,
    },
    ...LANDING_PAGES.map((p) => ({
      url: `${base}/${p.slug}`,
      lastModified: now,
      changeFrequency: 'monthly' as const,
      priority: 0.8,
    })),
    ...docEntries,
  ]
}
