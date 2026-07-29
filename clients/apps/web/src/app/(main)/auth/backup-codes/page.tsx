import LogoIcon from '@/components/Brand/logos/LogoIcon'
import { Metadata } from 'next'
import { metaTitle } from '@/utils/i18n'
import VerifyPage from './VerifyPage'
import { checkAuthenticationSession } from '@/utils/auth'
import { getServerSideAPI } from '@/utils/client/serverside'
import { redirect } from 'next/navigation'

export async function generateMetadata(): Promise<Metadata> {
  return { title: await metaTitle('backupCode') }
}

export default async function Page() {
  const api = await getServerSideAPI()
  const authenticationSession = await checkAuthenticationSession(api)
  if (!authenticationSession) {
    redirect('/auth')
  }

  return (
    <div className="dark:bg-outception-950 flex h-screen w-full grow items-center justify-center bg-white">
      <div className="flex w-80 flex-col items-center">
        <LogoIcon size={60} className="mb-6 text-black dark:text-white" />
        <div className="dark:text-outception-400 mb-6 text-center text-sm text-gray-500">
          Enter one of your backup codes
        </div>
        <VerifyPage />
      </div>
    </div>
  )
}
