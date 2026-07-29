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
import { getTranslations } from '@outception-com/i18n'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import { metaTitle, resolveLocale } from '@/utils/i18n'
import { redirect } from 'next/navigation'

export async function generateMetadata(): Promise<Metadata> {
  return { title: await metaTitle('login') }
}

export default async function Page(props: {
  searchParams: Promise<{
    error?: string
    return_to?: string
    from?: string
  }>
}) {
  if (!ACCOUNTS_ENABLED) {
    redirect('/')
  }
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

  const tr = getTranslations(await resolveLocale())

  return (
    <div className="flex h-screen w-full grow items-center justify-center">
      <div className="paper-panel flex w-full max-w-md flex-col justify-between gap-8 rounded-2xl p-12">
        <div className="flex flex-col gap-y-4">
          <Link href="/" aria-label="Outception home" className="w-fit">
            <LogoIcon size={60} className="text-black dark:text-white" />
          </Link>
          <div className="flex flex-col gap-4">
            <h2 className="text-2xl text-black dark:text-white">
              {tr.auth.welcome}
            </h2>
            <span className="dark:text-outception-400 text-lg text-balance text-gray-500">
              {tr.auth.tagline}
            </span>
          </div>
          {searchParams.error && (
            <div className="rounded-2xl bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
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
