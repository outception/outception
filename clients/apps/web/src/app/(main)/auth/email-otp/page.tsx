import LogoIcon from '@/components/Brand/logos/LogoIcon'
import { Metadata } from 'next'
import Link from 'next/link'
import VerifyPage from './VerifyPage'
import { checkAuthenticationSession } from '@/utils/auth'
import { getServerSideAPI } from '@/utils/client/serverside'
import { redirect } from 'next/navigation'

export const metadata: Metadata = {
  title: 'Enter verification code',
}

export default async function Page(props: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>
}) {
  const api = await getServerSideAPI()
  const authenticationSession = await checkAuthenticationSession(api)
  if (!authenticationSession) {
    redirect('/auth')
  }

  const searchParams = await props.searchParams
  const email = searchParams.email as string
  const intent = searchParams.intent as 'login' | 'signup' | undefined

  return (
    <div className="flex h-screen w-full grow items-center justify-center">
      <div className="flex w-80 flex-col items-center">
        <Link href="/" aria-label="Outception home" className="mb-6 w-fit">
          <LogoIcon size={60} className="text-black dark:text-white" />
        </Link>
        {intent === 'signup' && (
          <h1 className="mb-1 text-xl font-medium text-gray-700 dark:text-white">
            Welcome to Outception!
          </h1>
        )}
        <div className="dark:text-outception-400 mb-2 text-center text-gray-500">
          {intent === 'signup'
            ? 'To get started, we sent a verification code to '
            : 'We sent a verification code to '}
          <span className="dark:text-outception-300 font-medium text-gray-600">
            {email}
          </span>
        </div>
        <div className="dark:text-outception-400 mb-6 text-center text-sm text-gray-500">
          Please enter the 6-character code below
        </div>
        <VerifyPage intent={intent} />
      </div>
    </div>
  )
}
