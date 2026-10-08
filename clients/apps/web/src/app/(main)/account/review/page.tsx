import { ReviewQueue } from '@/components/Launches/ReviewQueue'
import { getAuthenticatedUser } from '@/utils/user'
import { getTranslations } from '@outception-com/i18n'
import type { Metadata } from 'next'
import { redirect } from 'next/navigation'

export function generateMetadata(): Metadata {
  return { title: getTranslations().launches.review.title }
}

/** The admin list only: anyone else is sent to their own products. The
 * server refuses the queue itself to everyone else as well. */
export default async function Page() {
  const user = await getAuthenticatedUser()
  if (!user?.is_admin) {
    redirect('/launches/mine')
  }
  return <ReviewQueue />
}
