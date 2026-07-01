import { NewsWall } from '@/components/News/NewsWall'
import { Metadata } from 'next'

export const metadata: Metadata = {
  // absolute: bypass the root "%s | Outception" template so the tab is just the
  // brand name.
  title: { absolute: 'Outception' },
  description:
    'A live wall of headlines from hundreds of sources. Promote what matters — pay to feature a post in any topic.',
  openGraph: {
    siteName: 'Outception',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
  },
}

export default function Page() {
  return <NewsWall />
}
