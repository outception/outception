import LogoIcon from '@/components/Brand/logos/LogoIcon'
import { Metadata } from 'next'
import { cookies } from 'next/headers'
import Link from 'next/link'
import Auth from '@/components/Auth/Auth'
import { getServerSideAPI } from '@/utils/client/serverside'
import {
  checkAuthenticationSession,
  getAuthenticationSessionRedirectPath,
} from '@/utils/auth'
import { schemas } from '@outception-com/client'
import { redirect } from 'next/navigation'

export const metadata: Metadata = {
  title: 'Log in to Outception',
}

export default async function Page(props: {
  searchParams: Promise<{
    error?: string
    return_to?: string
    from?: string
  }>
}) {
  const api = await getServerSideAPI()
  const authenticationSession = await checkAuthenticationSession(api)
  const searchParams = await props.searchParams

  const redirectPath = getAuthenticationSessionRedirectPath(
    authenticationSession,
  )
  if (redirectPath) {
    redirect(redirectPath)
  }

  const { return_to } = searchParams

  const cookieStore = await cookies()
  const lastLoginMethod =
    cookieStore.get('outception_last_login_method')?.value ?? null

  return (
    <div className="flex h-screen w-full grow items-center justify-center">
      <div className="glass-panel flex w-full max-w-md flex-col justify-between gap-8 rounded-3xl p-12">
        <div className="flex flex-col gap-y-4">
          <Link href="/" aria-label="Outception home" className="w-fit">
            <LogoIcon size={60} className="text-black dark:text-white" />
          </Link>
          <div className="flex flex-col gap-4">
            <h2 className="text-2xl text-black dark:text-white">
              Welcome to Outception
            </h2>
            <span className="dark:text-outception-400 text-lg text-balance text-gray-500">
              Live news, pay to promote
            </span>
          </div>
          {searchParams.error && (
            <div className="rounded-lg bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
              {searchParams.error}
            </div>
          )}
        </div>
        <Auth
          authenticationSession={authenticationSession}
          lastLoginMethod={lastLoginMethod as schemas['Factor'] | null}
          returnTo={return_to}
        />
      </div>
    </div>
  )
}
