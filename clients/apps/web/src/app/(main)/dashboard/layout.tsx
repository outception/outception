import { Toaster } from '@/components/Toast/Toaster'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import { redirect } from 'next/navigation'
import { PropsWithChildren, Suspense } from 'react'

export default async function Layout({ children }: PropsWithChildren) {
  if (!ACCOUNTS_ENABLED) {
    redirect('/')
  }
  return (
    <div className="flex h-full flex-col md:h-screen">
      {children}
      <Suspense>
        <Toaster />
      </Suspense>
    </div>
  )
}
