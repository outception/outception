import { ACCOUNTS_ENABLED } from '@/utils/features'
import { redirect } from 'next/navigation'
import { PropsWithChildren } from 'react'

// Accounts deactivated: bounce every /auth/* page (login, OTP, TOTP, backup
// codes) home so no auth UI is reachable. Backend auth routers are also
// unmounted, so the flow can't be driven directly either.
export default function AuthLayout({ children }: PropsWithChildren) {
  if (!ACCOUNTS_ENABLED) {
    redirect('/')
  }
  return children
}
