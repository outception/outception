import { CONFIG } from '@/utils/config'
import { PropsWithChildren } from 'react'
import LandingLayout from '../../../../components/Landing/LandingLayout'

// Rendered per request (not static) so the server can resolve the reader's
// locale from their cookies and render the wall already in their language -
// otherwise the shell paints in English and the client corrects it after
// hydration, flashing the UI chrome. See resolveLocale / LocaleProvider.
export const dynamic = 'force-dynamic'

// One @graph carrying everything an AI index wants to know in machine form:
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
        'A calm news wall: swipeable cards, one per source, with ' +
        'live headlines from hundreds of trusted outlets and AI summaries ' +
        'in your language.',
      offers: {
        '@type': 'Offer',
        price: '0',
        priceCurrency: 'USD',
        description:
          'Free to use on every platform, supported by one small ad.',
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
              'them, tap a headline for an AI summary, and reach the end.',
          },
        },
        {
          '@type': 'Question',
          name: 'Is Outception free?',
          acceptedAnswer: {
            '@type': 'Answer',
            text:
              'Yes. Outception is free on the web, iPhone and Android. It is ' +
              'supported by a single small ad, never full screen ads or paywalls.',
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
              'Hundreds of outlets across news, sports, finance, tech, ' +
              'science, entertainment and more, plus curated starter cards. ' +
              'Open More on the wall to search or pick a starter in one tap.',
          },
        },
      ],
    },
  ],
}

export default function Layout({ children }: PropsWithChildren) {
  return (
    <>
      <script
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
