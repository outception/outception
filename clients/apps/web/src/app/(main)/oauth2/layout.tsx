import { ACCOUNTS_ENABLED } from '@/utils/features'
import { redirect } from 'next/navigation'
import { PropsWithChildren } from 'react'

// Accounts deactivated: the app no longer acts as an OAuth2 provider, so the
// third-party authorize/consent UI is unreachable (the backend oauth2 router is
// also unmounted).
export default function OAuth2Layout({ children }: PropsWithChildren) {
  if (!ACCOUNTS_ENABLED) {
    redirect('/')
  }
  return children
}
