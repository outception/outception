import { CookieConsent } from '@/components/Privacy/CookieConsent'
import { SpectraBackground } from '@/components/Layout/SpectraBackground'
import { CONFIG } from '@/utils/config'
import { headers } from 'next/headers'
import { Metadata } from 'next/types'
import { OutceptionThemeProvider } from '../providers'

export async function generateMetadata(): Promise<Metadata> {
  const baseMetadata: Metadata = {
    title: {
      template: '%s | Outception',
      default: 'Outception',
    },
    description: 'A live news wall with pay-to-promote',
    openGraph: {
      type: 'website',
      siteName: 'Outception',
      title: 'Outception | A live news wall with pay-to-promote',
      description:
        'Follow 2,500+ news sources on one live wall, and pay to promote your post to the top.',
      locale: 'en_US',
    },
    twitter: {
      card: 'summary_large_image',
      title: 'Outception | A live news wall with pay-to-promote',
      description:
        'Follow 2,500+ news sources on one live wall, and pay to promote your post to the top.',
    },
    metadataBase: new URL(CONFIG.FRONTEND_BASE_URL),
    alternates: {
      canonical: CONFIG.FRONTEND_BASE_URL,
    },
  }

  return {
    ...baseMetadata,
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
  }
}

export default async function MainLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const headersList = await headers()
  const countryCode = headersList.get('x-vercel-ip-country')

  return (
    <OutceptionThemeProvider>
      <SpectraBackground />
      <link
        rel="preload"
        href="/fonts/Inter-Light.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/Inter-Regular.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/Inter-Medium.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/Inter-SemiBold.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/InterDisplay-Light.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/InterDisplay-Regular.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/InterDisplay-Medium.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/InterDisplay-SemiBold.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/Louize-Italic-205TF.otf"
        as="font"
        type="font/otf"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/GeistMono-Variable.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <div className="h-full bg-transparent dark:text-white">
        {children}
        <CookieConsent countryCode={countryCode} />
      </div>
    </OutceptionThemeProvider>
  )
}
