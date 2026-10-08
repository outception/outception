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
import type { Factor } from '@/utils/auth'
import { getTranslations } from '@outception-com/i18n'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import { metaTitle } from '@/utils/i18n'
import { redirect } from 'next/navigation'

/** What a provider sends back when the reader cancels or it declines
 * (the authorization error codes of the OAuth 2.0 standard; the server
 * passes them on as they are). */
const PROVIDER_REFUSALS = new Set([
  'access_denied',
  'consent_required',
  'interaction_required',
  'login_required',
  'unauthorized_client',
])

/** The messages the server itself redirects here with, and what the reader
 * reads for each. Anything else in the address is not shown: a crafted
 * link must not put its own words in the site's error box. */
const SIGN_IN_ERRORS: Record<string, 'expired' | 'method' | 'account'> = {
  'Factor not available for this session': 'method',
  'Invalid OAuth2 state': 'expired',
  'Missing OAuth2 state': 'expired',
  'Missing OAuth2 state cookie': 'expired',
  'No active authentication session': 'expired',
  'OAuth2 session expired': 'expired',
  'Authentication session cannot be completed': 'expired',
  'OAuth2 error': 'account',
  'User not found for authenticated identity': 'account',
}

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

  const tr = getTranslations()

  return (
    <div className="flex h-screen w-full grow items-center justify-center">
      <div className="paper-panel flex w-full max-w-md flex-col justify-between gap-8 rounded-2xl p-12">
        <div className="flex flex-col gap-y-4">
          <Link href="/" aria-label="Outception home" className="w-fit">
            <LogoIcon size={72} className="text-black dark:text-white" />
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
              {PROVIDER_REFUSALS.has(searchParams.error)
                ? tr.auth.providerRefused
                : Object.hasOwn(SIGN_IN_ERRORS, searchParams.error)
                  ? tr.auth.errors[SIGN_IN_ERRORS[searchParams.error]]
                  : tr.auth.failedBody}
            </div>
          )}
        </div>
        <Auth
          authenticationSession={authenticationSession}
          lastLoginMethod={lastLoginMethod as Factor | null}
          returnTo={return_to}
        />
      </div>
    </div>
  )
}
