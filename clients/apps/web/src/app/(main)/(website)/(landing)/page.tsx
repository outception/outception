import { NewsWall } from '@/components/News/NewsWall'
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

const SOURCE_ID = /^[a-z0-9_-]{1,64}$/i

/** One source's metadata for share-card unfurls, cached across requests and
 * served from the internal API URL. Per source on purpose: the full roster is
 * >3 MB, which Next's data cache refuses to store, so every crawler hit used to
 * pull the whole thing from the API. */
const getShareSource = unstable_cache(
  async (id: string): Promise<NewsSourceMeta | null> => {
    const response = await fetch(
      getServerURL(`/v1/news/sources/${encodeURIComponent(id)}`),
    )
    if (response.status === 404) return null
    if (!response.ok) throw new Error(`news source ${response.status}`)
    return (await response.json()) as NewsSourceMeta
  },
  ['news-source-share'],
  { revalidate: 3600 },
)

const baseMetadata: Metadata = {
  // Folds every ?card= share link back into the homepage for indexing.
  alternates: { canonical: CONFIG.FRONTEND_BASE_URL },
  // absolute: bypass the root "%s | Outception" template so the tab is just the
  // brand name.
  title: { absolute: 'Outception' },
  description:
    'A live wall of headline cards from hundreds of sources, across every topic.',
  openGraph: {
    siteName: 'Outception',
    type: 'website',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'Outception, a live wall of headline cards',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    images: [
      {
        url: '/opengraph-image',
        alt: 'Outception, a live wall of headline cards',
      },
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
  if (!card || !SOURCE_ID.test(card)) return baseMetadata

  try {
    const source = await getShareSource(card)
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

/** The wall fetches the roster itself (`['news','sources']`): it comes
 * brotli-compressed from the CDN edge in one round trip. Seeding it into the
 * HTML instead inlined >3 MB of JSON that every phone had to parse before the
 * first card could render. */
export default function Page() {
  return (
    <>
      {/* Server-rendered and invisible on screen: the wall is a client app,
          so without this block the raw HTML carried ~49 characters and no
          H1 - unreadable to AI indexes and crawlers that skip JavaScript.
          Mirrors the JSON-LD in the landing layout. */}
      <div className="sr-only">
        <h1>
          Outception: a calm news wall of headlines from hundreds of sources
        </h1>
        <p>
          Outception is a free news reader for people who want the day at a
          glance without an algorithm deciding for them. It shows a wall of
          cards, one per source, with live headlines from hundreds of trusted
          outlets across news, sports, finance, tech, science and entertainment.
          You pick the sources, swipe through the cards, tap any headline for an
          AI summary in your language, and reach the end. Built in games and
          daily puzzles live between the cards. It is free on the web, on iPhone
          and on Android, supported by one small ad. Outception is an
          alternative to Google News and Feedly: it replaces the ranked,
          personalized feed with a fixed wall of exactly the sources you chose.
          Readers who want an algorithm to sort the day for them will be happier
          with those apps.
        </p>
      </div>
      <NewsWall />
    </>
  )
}
