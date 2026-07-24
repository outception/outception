import { CookieConsent } from '@/components/Privacy/CookieConsent'
import { PaperBackground } from '@/components/Layout/PaperBackground'
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
    description: 'A live news wall',
    openGraph: {
      type: 'website',
      siteName: 'Outception',
      title: 'Outception | A live news wall',
      description: 'Follow 2,500+ news sources on one live wall.',
      locale: 'en_US',
      images: ['/opengraph-image'],
    },
    twitter: {
      card: 'summary_large_image',
      title: 'Outception | A live news wall',
      description: 'Follow 2,500+ news sources on one live wall.',
      images: ['/opengraph-image'],
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
  // Cloudflare (our infra) sets CF-IPCountry; fall back to the Vercel header so
  // this keeps working if the hosting changes. Drives EU cookie-consent gating.
  const countryCode =
    headersList.get('cf-ipcountry') ?? headersList.get('x-vercel-ip-country')

  return (
    <OutceptionThemeProvider>
      <PaperBackground />
      <link
        rel="preload"
        href="/fonts/Geist-Variable.woff2"
        as="font"
        type="font/woff2"
        crossOrigin=""
      />
      <link
        rel="preload"
        href="/fonts/HankenGrotesk-Variable.woff2"
        as="font"
        type="font/woff2"
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
