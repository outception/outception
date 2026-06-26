'use client'

import { AuthModal } from '@/components/Auth/AuthModal'
import GetStartedButton from '@/components/Auth/GetStartedButton'
import { Modal } from '@outception-com/orbit'
import { useModal } from '@/components/Modal/useModal'
import PublicProfileDropdown from '@/components/Navigation/PublicProfileDropdown'
import { usePostHog } from '@/hooks/posthog'
import { schemas } from '@outception-com/client'
import { Button } from '@outception-com/orbit'
import { usePathname } from 'next/navigation'

const TopbarRight = ({
  authenticatedUser,
}: {
  authenticatedUser?: schemas['UserRead']
}) => {
  const posthog = usePostHog()
  const pathname = usePathname()
  const loginReturnTo = pathname ?? '/start'
  const { isShown: isModalShown, hide: hideModal, show: showModal } = useModal()

  const onLoginClick = () => {
    posthog.capture('global:user:login:click')
    showModal()
  }

  return authenticatedUser ? (
    <div>
      <div className="relative flex w-max shrink-0 flex-row items-center justify-between gap-x-6">
        <PublicProfileDropdown
          authenticatedUser={authenticatedUser}
          className="shrink-0"
        />
      </div>
    </div>
  ) : (
    <>
      <Button onClick={onLoginClick} variant="secondary">
        Sign in
      </Button>

      <GetStartedButton
        className="hidden md:flex"
        size="default"
        text="Get started"
      />

      <Modal
        title="Sign in"
        isShown={isModalShown}
        hide={hideModal}
        modalContent={<AuthModal returnTo={loginReturnTo} />}
        className="lg:w-full lg:max-w-[480px]"
      />
    </>
  )
}

export default TopbarRight
