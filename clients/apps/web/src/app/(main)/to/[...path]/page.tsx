import { redirect } from 'next/navigation'

// Deep-link redirect kept for links in the wild: /to/<rest> opens the
// reader's account area at <rest>, or the wall when there is no rest.
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
  const rest = path.filter((p) => p !== 'dashboard').join('/')
  redirect(rest ? `/account/${rest}${qs}` : `/account/news${qs}`)
}
