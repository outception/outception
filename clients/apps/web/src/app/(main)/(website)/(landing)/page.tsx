import { NewsWall } from '@/components/News/NewsWall'
import { newsApi } from '@/utils/news'
import {
  DEFAULT_LOCALE,
  getTranslations,
  isAcceptedLocale,
} from '@outception-com/i18n'
import { Metadata } from 'next'

const baseMetadata: Metadata = {
  // absolute: bypass the root "%s | Outception" template so the tab is just the
  // brand name.
  title: { absolute: 'Outception' },
  description:
    'A live wall of headlines from hundreds of sources, across every topic.',
  openGraph: {
    siteName: 'Outception',
    type: 'website',
    images: [
      {
        url: '/opengraph-image',
        width: 1200,
        height: 630,
        alt: 'Outception — a live wall of headlines',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    images: [
      { url: '/opengraph-image', alt: 'Outception — a live wall of headlines' },
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
    const sources = await newsApi.sources()
    const source = sources.find((s) => s.id === card)
    if (!source) return baseMetadata

    const locale = lang && isAcceptedLocale(lang) ? lang : DEFAULT_LOCALE
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

export default function Page() {
  return <NewsWall />
}
