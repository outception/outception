import { AccountLayout } from '@/components/Layout/AccountLayout'
import { Toaster } from '@/components/Toast/Toaster'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import { redirect } from 'next/navigation'
import { PropsWithChildren, Suspense } from 'react'

export default function Layout({ children }: PropsWithChildren) {
  if (!ACCOUNTS_ENABLED) {
    redirect('/')
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
