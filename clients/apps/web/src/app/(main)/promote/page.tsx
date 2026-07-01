import { getLastVisitedOrg } from '@/utils/cookies'
import { getAuthenticatedUser } from '@/utils/user'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

// Hand-off target for the mobile apps: promotions are paid on the web, so the
// native "Promote" button opens this URL. Middleware gates it (see proxy.ts),
// so the user is authenticated by the time we get here; we just resolve their
// organization and drop them on the promotions page with the compose dialog
// already open.
export default async function Page() {
  const user = await getAuthenticatedUser()
  const organizations = user?.organizations ?? []
  if (organizations.length === 0) {
    redirect('/dashboard')
  }

  const organization =
    getLastVisitedOrg(await cookies(), organizations) ?? organizations[0]
  redirect(`/dashboard/${organization.slug}/promotions?compose=1`)
}
