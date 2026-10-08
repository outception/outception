import { PaperBackground } from '@/components/Layout/PaperBackground'
import { CONFIG } from '@/utils/config'
import { headers } from 'next/headers'
import { Metadata } from 'next/types'
import { Suspense } from 'react'
import { OutceptionThemeProvider } from '../providers'

// The API lives on a different host, so the first request otherwise pays a cold
// DNS + TCP + TLS handshake. Warm it alongside the font preloads.
const API_ORIGIN = new URL(CONFIG.BASE_URL).origin

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
      description: 'Follow 8,000+ news sources on one live wall.',
      locale: 'en_US',
      images: ['/opengraph-image'],
    },
    twitter: {
      card: 'summary_large_image',
      title: 'Outception | A live news wall',
      description: 'Follow 8,000+ news sources on one live wall.',
      images: ['/opengraph-image'],
    },
    metadataBase: new URL(CONFIG.FRONTEND_BASE_URL),
    // No `alternates.canonical` here: layout metadata is inherited, so every
    // page under (main) - /terms, /privacy - would declare the homepage as its
    // canonical and get dropped from the index as a duplicate. The landing
    // page sets its own (it genuinely wants ?card= links folded into /).
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
  const nonce = (await headers()).get('x-nonce') ?? undefined
  // The theme provider reads the search params (a `?theme=` override), so
  // it sits under a Suspense boundary; the pages render per request anyway,
  // since the layouts read the request's nonce.
  return (
    <Suspense>
      <OutceptionThemeProvider nonce={nonce}>
        <PaperBackground />
        <link rel="dns-prefetch" href={API_ORIGIN} />
        <link
          rel="preconnect"
          href={API_ORIGIN}
          crossOrigin="use-credentials"
        />
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
        <div className="h-full bg-transparent dark:text-white">{children}</div>
      </OutceptionThemeProvider>
    </Suspense>
  )
}
