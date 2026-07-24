import { CONFIG } from '@/utils/config'
import { PropsWithChildren } from 'react'
import LandingLayout from '../../../../components/Landing/LandingLayout'

// Rendered per request (not static) so the server can resolve the reader's
// locale from their cookies and render the wall already in their language —
// otherwise the shell paints in English and the client corrects it after
// hydration, flashing the UI chrome. See resolveLocale / LocaleProvider.
export const dynamic = 'force-dynamic'

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: 'Outception',
  url: CONFIG.FRONTEND_BASE_URL,
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
