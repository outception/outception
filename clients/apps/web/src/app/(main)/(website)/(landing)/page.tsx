import { NewsWall } from '@/components/News/NewsWall'
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
} from '@tanstack/react-query'
import { getServerURL } from '@/utils/api'
import { CONFIG } from '@/utils/config'
import type { NewsSourceMeta } from '@/utils/news'
import { unstable_cache } from 'next/cache'
import {
  DEFAULT_LOCALE,
  getTranslations,
  isAcceptedLocale,
  loadTranslations,
} from '@outception-com/i18n'
import { Metadata } from 'next'

/** Source roster for share-card metadata. Cached across requests and served
 * from the internal API URL: the previous call went through the BROWSER client
 * on an uncached fetch, so every Slack/WhatsApp/Twitter unfurl and every
 * crawler hit pulled the entire multi-thousand-source payload over the public
 * URL — and installed a client-only toast middleware into a server render. */
const getShareSources = unstable_cache(
  async (): Promise<NewsSourceMeta[]> => {
    const response = await fetch(getServerURL('/v1/news/sources'))
    if (!response.ok) return []
    return (await response.json()) as NewsSourceMeta[]
  },
  ['news-sources-share'],
  { revalidate: 3600 },
)

const baseMetadata: Metadata = {
  // Folds every ?card= share link back into the homepage for indexing.
  alternates: { canonical: CONFIG.FRONTEND_BASE_URL },
  // absolute: bypass the root "%s | Outception" template so the tab is just the
  // brand name.
  title: { absolute: 'Outception' },
  description:
    'A live deck of headlines from hundreds of sources, across every topic.',
  openGraph: {
    siteName: 'Outception',
    type: 'website',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'Outception — a live deck of headlines',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    images: [
      { url: '/opengraph-image', alt: 'Outception — a live deck of headlines' },
    ],
  },
}

/** A shared card link (`?card=<id>&lang=<locale>`) gets a per-card preview: the
 * source's name + a subtitle in the sharer's language, rendered as a dynamic
 * OpenGraph image so the unfurled card reflects exactly what was shared. */
export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ card?: string; lang?: string }>
}): Promise<Metadata> {
  const { card, lang } = await searchParams
  if (!card) return baseMetadata

  try {
    const sources = await getShareSources()
    const source = sources.find((s) => s.id === card)
    if (!source) return baseMetadata

    const locale = lang && isAcceptedLocale(lang) ? lang : DEFAULT_LOCALE
    await loadTranslations(locale)
    const subtitle = getTranslations(locale).news.share.ogSubtitle
    const heading = `${source.name} · Outception`
    const image = `/og/card?title=${encodeURIComponent(
      source.name,
    )}&subtitle=${encodeURIComponent(subtitle)}&color=${encodeURIComponent(
      source.color,
    )}`

    return {
      ...baseMetadata,
      title: { absolute: heading },
      description: subtitle,
      openGraph: {
        siteName: 'Outception',
        type: 'website',
        title: heading,
        description: subtitle,
        images: [{ url: image, width: 1200, height: 630, alt: heading }],
      },
      twitter: {
        card: 'summary_large_image',
        title: heading,
        description: subtitle,
        images: [{ url: image, alt: heading }],
      },
    }
  } catch {
    return baseMetadata
  }
}

export default async function Page() {
  // The roster is already fetched server-side (share metadata above, cached
  // for an hour) — hand the same payload to the client's query cache so first
  // paint doesn't wait on a second 1.3 MB round trip for ['news','sources'].
  const queryClient = new QueryClient()
  const sources = await getShareSources()
  if (sources.length > 0) {
    queryClient.setQueryData(['news', 'sources'], sources)
  }
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <NewsWall />
    </HydrationBoundary>
  )
}
