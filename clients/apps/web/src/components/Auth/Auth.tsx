'use client'

import { useT } from '@/providers/translate'
import { schemas } from '@outception-com/client'
import type { Factor } from '@/utils/auth'
import { Fragment } from 'react'
import GoogleLoginButton from './GoogleLoginButton'
import EmailOTPForm from './EmailOTPForm'
import AppleLoginButton from './AppleLoginButton'
import MicrosoftLoginButton from './MicrosoftLoginButton'

type OAuthFactor = Exclude<Factor, 'email_otp' | 'totp'>
const OAUTH_FACTORS: OAuthFactor[] = ['apple', 'microsoft', 'google']

const isOAuthFactor = (
  value: Factor | null | undefined,
): value is OAuthFactor =>
  !!value && (OAUTH_FACTORS as string[]).includes(value)

const Auth = ({
  authenticationSession,
  lastLoginMethod,
  returnTo,
  signup,
}: {
  authenticationSession: schemas['AuthenticationSession'] | null
  lastLoginMethod?: Factor | null
  returnTo?: string
  signup?: boolean
}) => {
  const t = useT()

  const primaryOAuthFactor: OAuthFactor = isOAuthFactor(lastLoginMethod)
    ? lastLoginMethod
    : 'google'
  const orderedOAuthFactors: OAuthFactor[] = [
    primaryOAuthFactor,
    ...OAUTH_FACTORS.filter(
      (f) => isOAuthFactor(f) && f !== primaryOAuthFactor,
    ),
  ]

  const renderOAuth = (factor: OAuthFactor, isPrimary: boolean) => {
    const variant = isPrimary ? 'default' : 'secondary'
    switch (factor) {
      case 'apple':
        return (
          <AppleLoginButton
            authenticationSession={authenticationSession}
            variant={variant}
            returnTo={returnTo}
            signup={signup}
          />
        )
      case 'microsoft':
        return (
          <MicrosoftLoginButton
            authenticationSession={authenticationSession}
            variant={variant}
            returnTo={returnTo}
            signup={signup}
          />
        )
      case 'google':
        return (
          <GoogleLoginButton
            authenticationSession={authenticationSession}
            variant={variant}
            returnTo={returnTo}
            signup={signup}
          />
        )
    }
  }

  return (
    <div className="flex flex-col gap-y-4">
      <div className="flex w-full flex-col gap-y-4">
        {orderedOAuthFactors.map((factor, index) => (
          <Fragment key={factor}>
            <LastUsedWrapper show={lastLoginMethod === factor}>
              {renderOAuth(factor, index === 0)}
            </LastUsedWrapper>
          </Fragment>
        ))}
        <div className="flex w-full flex-row items-center gap-6">
          <div className="dark:border-outception-700 grow border-t border-gray-200" />
          <div className="text-sm text-gray-500">{t('auth.or')}</div>
          <div className="dark:border-outception-700 grow border-t border-gray-200" />
        </div>
        <LastUsedWrapper show={lastLoginMethod === 'email_otp'}>
          <EmailOTPForm
            authenticationSession={authenticationSession}
            returnTo={returnTo}
            signup={signup}
          />
        </LastUsedWrapper>
      </div>
    </div>
  )
}

const LastUsedWrapper = ({
  show,
  children,
}: {
  show: boolean
  children: React.ReactNode
}) => {
  const t = useT()
  return (
    <div className="relative">
      {show && (
        <span className="dark:bg-outception-900 dark:border-outception-600 absolute -top-3 -right-2 z-20 rounded-full border border-gray-200 bg-white px-2 py-0.5 text-xs text-black dark:text-white">
          {t('auth.lastUsed')}
        </span>
      )}
      {children}
    </div>
  )
}

export default Auth
