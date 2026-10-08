import { headers } from 'next/headers'
import { CONFIG } from '@/utils/config'
import { PropsWithChildren } from 'react'
import LandingLayout from '../../../../components/Landing/LandingLayout'

// Rendered per request (not static) so the server can read the reader's
// country - from the edge header, or the cookie the proxy mirrors it
// into - and seed their national cards and local weather on first paint.
// Static, the shell would paint a default set and the client would correct
// it after hydration, visibly reshuffling the wall.
export const dynamic = 'force-dynamic'

// One @graph carrying everything an answer engine wants to know in machine form:
// the site, the organization behind it, the product (free, and saying so
// explicitly), and the questions people actually ask. Content mirrors the
// server-rendered plain statement on the homepage.
const jsonLd = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': 'WebSite',
      '@id': `${CONFIG.FRONTEND_BASE_URL}/#website`,
      name: 'Outception',
      url: CONFIG.FRONTEND_BASE_URL,
      publisher: { '@id': `${CONFIG.FRONTEND_BASE_URL}/#org` },
    },
    {
      '@type': 'Organization',
      '@id': `${CONFIG.FRONTEND_BASE_URL}/#org`,
      name: 'Outception',
      url: CONFIG.FRONTEND_BASE_URL,
      logo: `${CONFIG.FRONTEND_BASE_URL}/icon-512.png`,
      sameAs: ['https://apps.apple.com/app/id6793827093'],
    },
    {
      '@type': 'SoftwareApplication',
      '@id': `${CONFIG.FRONTEND_BASE_URL}/#app`,
      name: 'Outception',
      applicationCategory: 'NewsApplication',
      operatingSystem: 'Web, iOS, Android',
      url: CONFIG.FRONTEND_BASE_URL,
      installUrl: 'https://apps.apple.com/app/id6793827093',
      description:
        'A calm news wall: swipeable cards, one per publisher, with ' +
        'live headlines from over ten thousand outlets, a short summary on ' +
        'tap and live tables.',
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
        description:
          'Free to use on every platform. No ad network; one products card a day, chosen by hand.',
      },
    },
    {
      '@type': 'FAQPage',
      '@id': `${CONFIG.FRONTEND_BASE_URL}/#faq`,
      mainEntity: [
        {
          '@type': 'Question',
          name: 'What is Outception?',
          acceptedAnswer: {
            '@type': 'Answer',
            text:
              'Outception is a news reader shaped like a wall of cards. Each ' +
              'card is one source with its live headlines. You swipe through ' +
              'them, tap a headline for a short summary, and reach the end.',
          },
        },
        {
          '@type': 'Question',
          name: 'Is Outception free?',
          acceptedAnswer: {
            '@type': 'Answer',
            text:
              'Yes. Outception is free on the web, iPhone and Android. There ' +
              'is no ad network and no paywall; one products card a day, ' +
              'chosen by hand, is the only commercial surface.',
          },
        },
        {
          '@type': 'Question',
          name: 'How is it different from algorithmic news feeds?',
          acceptedAnswer: {
            '@type': 'Answer',
            text:
              'There is no ranking and no engagement loop. You choose the ' +
              'sources, the wall shows exactly those, and the wall has an ' +
              'explicit end. Readers who want personalized ranked feeds may ' +
              'prefer Google News or Feedly; Outception is deliberately the ' +
              'opposite.',
          },
        },
        {
          '@type': 'Question',
          name: 'Which sources can I follow?',
          acceptedAnswer: {
            '@type': 'Answer',
            text:
              'Over ten thousand outlets across news, sports, finance, tech, ' +
              'science, entertainment and more, plus curated starter cards. ' +
              'Open More on the wall to search or pick a starter in one tap.',
          },
        },
      ],
    },
  ],
}

export default async function Layout({ children }: PropsWithChildren) {
  const nonce = (await headers()).get('x-nonce') ?? undefined
  return (
    <>
      <script
        nonce={nonce}
        type="application/ld+json"
        // eslint-disable-next-line react/no-danger
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c'),
        }}
      />
      <LandingLayout>{children}</LandingLayout>
    </>
  )
}
