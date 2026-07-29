import { LANDING_PAGES, landingPageBySlug } from '@/lib/seo/landingPages'
import { CONFIG } from '@/utils/config'
import { Button, Text } from '@outception-com/orbit'
import { Box } from '@outception-com/orbit/Box'
import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'

// Only the listed slugs exist; anything else 404s instead of soft-matching.
export const dynamicParams = false

export function generateStaticParams() {
  return LANDING_PAGES.map((p) => ({ slug: p.slug }))
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>
}): Promise<Metadata> {
  const page = landingPageBySlug((await params).slug)
  if (!page) return {}
  return {
    title: page.title,
    description: page.description,
    alternates: {
      canonical: `${CONFIG.FRONTEND_BASE_URL.replace(/\/$/, '')}/${page.slug}`,
    },
  }
}

export default async function SeoLandingPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const page = landingPageBySlug((await params).slug)
  if (!page) notFound()
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
              No signup, no install needed — the wall opens on your country’s
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
