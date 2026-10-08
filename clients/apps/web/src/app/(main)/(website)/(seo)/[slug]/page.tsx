import { CrawlerPage } from '@/components/Seo/CrawlerPage'
import {
  cityPage,
  countryPage,
  parseCrawlerSlug,
  starterPage,
  type CrawlerPageData,
} from '@/lib/seo/crawler'
import { LANDING_PAGES, landingPageBySlug } from '@/lib/seo/landingPages'
import { CONFIG } from '@/utils/config'
import { getTranslations, translate } from '@outception-com/i18n'
import { Button } from '@outception-com/orbit/Button'
import { Text } from '@outception-com/orbit/Text'
import { Box } from '@outception-com/orbit/Box'
import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'

// The comparison pages are static; the country, city and Starter pages render
// from the edge-cached data and refresh every hour.
export const revalidate = 3600

export function generateStaticParams() {
  return LANDING_PAGES.map((p) => ({ slug: p.slug }))
}

const base = () => CONFIG.FRONTEND_BASE_URL.replace(/\/$/, '')

/** The crawler page for a slug, or null when the slug names nothing. */
const crawlerData = async (slug: string): Promise<CrawlerPageData | null> => {
  const parsed = parseCrawlerSlug(slug)
  if (!parsed) return null
  if (parsed.kind === 'country') {
    return countryPage(parsed.code, {
      title: (country) => translate('news.crawler.countryTitle', { country }),
      intro: (country) => translate('news.crawler.countryIntro', { country }),
    })
  }
  if (parsed.kind === 'city') {
    return cityPage(parsed.id, {
      title: (city) => translate('news.crawler.cityTitle', { city }),
      intro: (city) => translate('news.crawler.cityIntro', { city }),
    })
  }
  const names = getTranslations().news.templates.names as Record<string, string>
  return starterPage(parsed.id, names, {
    title: (name) => translate('news.crawler.starterTitle', { name }),
    intro: (name) => translate('news.crawler.starterIntro', { name }),
  })
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  const { slug } = await params
  const page = landingPageBySlug(slug)
  if (page) {
    return {
      title: page.title,
      description: page.description,
      alternates: { canonical: `${base()}/${page.slug}` },
    }
  }
  const data = await crawlerData(slug)
  if (!data) return {}
  const image = `/og/card?title=${encodeURIComponent(data.title)}&subtitle=${encodeURIComponent(translate('news.share.ogSubtitle'))}&variant=set`
  return {
    title: data.title,
    description: data.intro,
    // Canonical to the wall: the page is a doorway, the wall is the product.
    alternates: { canonical: `${base()}${data.wallPath}` },
    openGraph: {
      siteName: 'Outception',
      type: 'website',
      title: data.title,
      description: data.intro,
      images: [{ url: image, width: 1200, height: 630, alt: data.title }],
    },
    twitter: {
      card: 'summary_large_image',
      title: data.title,
      images: [{ url: image }],
    },
  }
}

export default async function SeoLandingPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  const page = landingPageBySlug(slug)
  if (!page) {
    const data = await crawlerData(slug)
    if (!data) notFound()
    return (
      <CrawlerPage
        data={data}
        labels={{
          open: translate('news.crawler.open'),
          openCard: translate('news.crawler.openCard'),
          updated: translate('news.crawler.updated'),
          more:
            data.moreSources > 0
              ? translate('news.crawler.moreSources', {
                  count: data.moreSources,
                })
              : null,
        }}
      />
    )
  }
  return (
    <Box justifyContent="center" paddingHorizontal="l" paddingVertical="3xl">
      <Box
        as="article"
        flexDirection="column"
        rowGap="xl"
        maxWidth={720}
        width="100%"
      >
        <Text variant="heading-m" as="h1" serif>
          {page.h1}
        </Text>
        {page.intro.map((p) => (
          <Text key={p.slice(0, 24)} color="muted">
            {p}
          </Text>
        ))}
        {page.sections.map((section) => (
          <Box
            key={section.heading}
            as="section"
            flexDirection="column"
            rowGap="m"
          >
            <Text variant="heading-xs" as="h2">
              {section.heading}
            </Text>
            <Box as="ul" flexDirection="column" rowGap="s">
              {section.body.map((line) => (
                <Box key={line.slice(0, 32)} as="li" display="block">
                  <Text color="muted">{line}</Text>
                </Box>
              ))}
            </Box>
          </Box>
        ))}
        <Box
          flexDirection="column"
          alignItems="center"
          rowGap="m"
          borderRadius="l"
          backgroundColor="background-card"
          borderWidth={1}
          borderStyle="solid"
          borderColor="border-primary"
          padding="xl"
        >
          <Text variant="heading-xs" as="h2">
            See your wall in ten seconds
          </Text>
          <div className="text-center">
            <Text color="muted">
              No signup, no install needed - the wall opens on your country’s
              edition and you take it from there.
            </Text>
          </div>
          <Link href="/">
            <Button>Open Outception</Button>
          </Link>
        </Box>
      </Box>
    </Box>
  )
}
