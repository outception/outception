'use client'

import {
  useAuth,
  useDisconnectOAuthAccount,
  useMicrosoftAccount,
  useGoogleAccount,
} from '@/hooks'
import {
  getMicrosoftAuthorizeLinkURL,
  getGoogleAuthorizeLinkURL,
} from '@/utils/auth'
import AlternateEmailOutlined from '@mui/icons-material/AlternateEmailOutlined'
import Microsoft from '@mui/icons-material/Microsoft'
import Google from '@mui/icons-material/Google'
import { schemas } from '@outception-com/client'
import { Button } from '@outception-com/orbit'
import { ListGroup } from '@outception-com/orbit'
import { usePathname, useSearchParams } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import EmailUpdateForm from '../Form/EmailUpdateForm'
import { twMerge } from 'tailwind-merge'
import { useT } from '@/providers/locale'
import { toast } from '@/components/Toast/use-toast'

const AuthenticationMethod = ({
  icon,
  title,
  subtitle,
  action,
  hideTitle = false,
  error,
}: {
  icon: React.ReactNode
  title: React.ReactNode
  subtitle: React.ReactNode
  action: React.ReactNode
  hideTitle?: boolean
  error?: string
}) => {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-center">
        <div
          className={twMerge('self-start', !hideTitle && 'relative top-[3px]')}
        >
          {icon}
        </div>
        {!hideTitle && (
          <div className="grow">
            <div className="font-medium">{title}</div>
            <div className="dark:text-outception-500 text-sm text-gray-500">
              {subtitle}
            </div>
          </div>
        )}
        <div className={hideTitle ? 'w-full' : 'flex-0'}>{action}</div>
      </div>
      {error && (
        <div className="flex justify-end text-sm text-red-500">{error}</div>
      )}
    </div>
  )
}

const MicrosoftAuthenticationMethod = ({
  oauthAccount,
  returnTo,
  onDisconnect,
  isDisconnecting,
  error,
}: {
  oauthAccount: schemas['OAuthAccountRead'] | undefined
  returnTo: string
  onDisconnect: () => void
  isDisconnecting: boolean
  error?: string
}) => {
  const t = useT()
  const authorizeURL = getMicrosoftAuthorizeLinkURL(returnTo)

  return (
    <AuthenticationMethod
      icon={<Microsoft />}
      title={
        oauthAccount
          ? oauthAccount.account_username
            ? `${oauthAccount.account_username} (${oauthAccount.account_email})`
            : oauthAccount.account_email
          : t('account.authMethods.connectMicrosoft')
      }
      subtitle={
        oauthAccount
          ? t('account.authMethods.microsoftConnected')
          : t('account.authMethods.microsoftConnect')
      }
      action={
        oauthAccount ? (
          <Button
            variant="secondary"
            onClick={onDisconnect}
            loading={isDisconnecting}
          >
            {t('account.authMethods.disconnect')}
          </Button>
        ) : (
          <Button asChild>
            <a href={authorizeURL}>{t('account.authMethods.connect')}</a>
          </Button>
        )
      }
      error={error}
    />
  )
}

const GoogleAuthenticationMethod = ({
  oauthAccount,
  returnTo,
  onDisconnect,
  isDisconnecting,
  error,
}: {
  oauthAccount: schemas['OAuthAccountRead'] | undefined
  returnTo: string
  onDisconnect: () => void
  isDisconnecting: boolean
  error?: string
}) => {
  const t = useT()
  const authorizeURL = getGoogleAuthorizeLinkURL(returnTo)

  return (
    <AuthenticationMethod
      icon={<Google />}
      title={
        oauthAccount
          ? oauthAccount.account_email
          : t('account.authMethods.connectGoogle')
      }
      subtitle={
        oauthAccount
          ? t('account.authMethods.googleConnected')
          : t('account.authMethods.googleConnect')
      }
      action={
        oauthAccount ? (
          <Button
            variant="secondary"
            onClick={onDisconnect}
            loading={isDisconnecting}
          >
            {t('account.authMethods.disconnect')}
          </Button>
        ) : (
          <Button asChild>
            <a href={authorizeURL}>{t('account.authMethods.connect')}</a>
          </Button>
        )
      }
      error={error}
    />
  )
}

const AuthenticationSettings = () => {
  const t = useT()
  const { currentUser, reloadUser } = useAuth()
  const pathname = usePathname()
  const microsoftAccount = useMicrosoftAccount()
  const googleAccount = useGoogleAccount()
  const disconnectOAuth = useDisconnectOAuthAccount()
  const listGroupRef = useRef<HTMLDivElement>(null)

  const disconnect = (platform: 'microsoft' | 'google') =>
    disconnectOAuth.mutate(platform, {
      onError: () =>
        toast({
          title: t('account.authMethods.disconnectError'),
          variant: 'error',
        }),
    })

  const searchParams = useSearchParams()
  const [updateEmailStage, setUpdateEmailStage] = useState<
    'off' | 'form' | 'request' | 'verified'
  >((searchParams.get('update_email') as 'verified' | null) || 'off')
  const userReloaded = useRef(false)

  const oauthLinkError =
    searchParams.get('type') === 'oauth_link_error' && searchParams.get('error')
  const oauthLinkFactor = searchParams.get('factor')

  useEffect(() => {
    if (!userReloaded.current && updateEmailStage === 'verified') {
      reloadUser()
      userReloaded.current = true
    }
  }, [updateEmailStage, reloadUser])

  useEffect(() => {
    if (oauthLinkError && listGroupRef.current) {
      requestAnimationFrame(() => {
        listGroupRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      })
    }
  }, [oauthLinkError])

  const updateEmailContent: Record<
    'off' | 'form' | 'request' | 'verified',
    React.ReactNode
  > = {
    off: (
      <div className="flex flex-row items-center gap-4">
        {currentUser && (
          <Button onClick={() => setUpdateEmailStage('form')}>
            {t('account.authMethods.changeEmail')}
          </Button>
        )}
      </div>
    ),
    form: (
      <EmailUpdateForm
        onEmailUpdateRequest={() => setUpdateEmailStage('request')}
        onCancel={() => setUpdateEmailStage('off')}
        returnTo={`${pathname}?update_email=verified`}
      />
    ),
    request: (
      <div className="dark:text-outception-300 dark:bg-outception-600 flex h-10 items-center justify-center rounded-lg bg-gray-100 text-center text-sm text-gray-500">
        {t('account.authMethods.verificationSent')}
      </div>
    ),
    verified: (
      <div className="flex h-10 items-center justify-center rounded-lg bg-green-50 text-center text-sm text-green-700 dark:bg-green-950 dark:text-green-500">
        {t('account.authMethods.emailUpdated')}
      </div>
    ),
  }

  return (
    <div ref={listGroupRef}>
      <ListGroup>
        <ListGroup.Item>
          <MicrosoftAuthenticationMethod
            oauthAccount={microsoftAccount}
            returnTo={pathname || '/start'}
            onDisconnect={() => disconnect('microsoft')}
            isDisconnecting={disconnectOAuth.isPending}
            error={
              oauthLinkError && oauthLinkFactor === 'microsoft'
                ? oauthLinkError
                : undefined
            }
          />
        </ListGroup.Item>

        <ListGroup.Item>
          <GoogleAuthenticationMethod
            oauthAccount={googleAccount}
            returnTo={pathname || '/start'}
            onDisconnect={() => disconnect('google')}
            isDisconnecting={disconnectOAuth.isPending}
            error={
              oauthLinkError && oauthLinkFactor === 'google'
                ? oauthLinkError
                : undefined
            }
          />
        </ListGroup.Item>

        <ListGroup.Item>
          <AuthenticationMethod
            icon={<AlternateEmailOutlined />}
            title={currentUser?.email}
            subtitle={t('account.authMethods.emailHint')}
            action={updateEmailContent[updateEmailStage]}
            hideTitle={updateEmailStage !== 'off'}
          />
        </ListGroup.Item>
      </ListGroup>
    </div>
  )
}

export default AuthenticationSettings
