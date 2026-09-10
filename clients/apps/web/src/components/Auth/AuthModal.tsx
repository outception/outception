'use client'

import Auth from '@/components/Auth/Auth'
import { useT } from '@/providers/locale'
import { type schemas } from '@outception-com/client'

interface AuthModalProps {
  returnTo?: string
  signup?: boolean
}

export const AuthModal = ({ returnTo, signup }: AuthModalProps) => {
  const isSignup = signup !== undefined
  const t = useT()

  const lastLoginMethod =
    typeof document !== 'undefined'
      ? ((document.cookie.match(/outception_last_login_method=(\w+)/)?.[1] ??
          null) as schemas['Factor'])
      : null

  return (
    <div className="overflow-y-auto p-12">
      <div className="flex flex-col justify-between gap-y-12">
        {isSignup && (
          <div className="flex flex-col gap-y-1">
            <h1 className="text-xl font-medium">{t('auth.welcome')}</h1>
            <p className="dark:text-outception-500 text-sm text-gray-500">
              {t('auth.tagline')}
            </p>
          </div>
        )}

        <div className="flex flex-col gap-y-12">
          <Auth
            authenticationSession={null}
            returnTo={returnTo}
            signup={signup}
            lastLoginMethod={lastLoginMethod}
          />
        </div>
      </div>
    </div>
  )
}
