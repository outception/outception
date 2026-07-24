import { getLastVisitedOrg } from '@/utils/cookies'
import { getUserOrganizations } from '@/utils/user'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

// Deep-link redirect: /to/dashboard/<rest> → /dashboard/<user-org>/<rest>
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ path: string[] }>
  searchParams: Promise<Record<string, string>>
}) {
  const { path } = await params
  const resolvedSearchParams = await searchParams
  const query = new URLSearchParams(resolvedSearchParams).toString()
  const qs = query ? `?${query}` : ''

  const userOrganizations = await getUserOrganizations()

  if (userOrganizations.length === 0) {
    // Safety net: a personal org is auto-provisioned on login. Send to the
    // dashboard (resolves the org) rather than the removed onboarding flow.
    redirect(`/dashboard${qs}`)
  }

  const organization =
    getLastVisitedOrg(await cookies(), userOrganizations) ??
    userOrganizations[0]

  if (path[0] !== 'dashboard') {
    redirect(`/dashboard/${organization.slug}${qs}`)
  }

  const rest = path.slice(1).join('/')
  const tail = rest ? `/${rest}` : ''
  redirect(`/dashboard/${organization.slug}${tail}${qs}`)
}
