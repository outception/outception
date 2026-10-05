import { AccountLayout } from '@/components/Layout/AccountLayout'
import { Toaster } from '@/components/Toast/Toaster'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import { redirect } from 'next/navigation'
import { PropsWithChildren, Suspense } from 'react'

/** Submitting and the reader's own list sit in the signed-in area; the
 * proxy sends a visitor to sign in first. */
export default function Layout({ children }: PropsWithChildren) {
  if (!ACCOUNTS_ENABLED) {
    redirect('/launches')
  }
  return (
    <AccountLayout>
      {children}
      <Suspense>
        <Toaster />
      </Suspense>
    </AccountLayout>
  )
}
