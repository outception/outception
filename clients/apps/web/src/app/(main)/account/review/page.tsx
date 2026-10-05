import { ReviewQueue } from '@/components/Launches/ReviewQueue'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'

export function generateMetadata(): Metadata {
  return { title: getTranslations().launches.review.title }
}

/** The server allows only the admin list through; the page shows the
 * refusal line to anyone else. */
export default function Page() {
  return <ReviewQueue />
}
