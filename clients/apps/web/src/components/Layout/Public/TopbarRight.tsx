'use client'

import { AuthModal } from '@/components/Auth/AuthModal'
import GetStartedButton from '@/components/Auth/GetStartedButton'
import { Modal } from '@outception-com/orbit/Modal'
import { useModal } from '@/components/Modal/useModal'
import PublicProfileDropdown from '@/components/Navigation/PublicProfileDropdown'
import { ACCOUNTS_ENABLED } from '@/utils/features'
import { schemas } from '@outception-com/client'
import { Button } from '@outception-com/orbit/Button'
import { usePathname } from 'next/navigation'

const TopbarRight = ({
  authenticatedUser,
  menuPlacement = 'below',
}: {
  authenticatedUser?: schemas['UserRead']
  menuPlacement?: 'below' | 'above'
}) => {
  // Accounts deactivated - no sign-in entry point in the UI. (Guard before any
  // hooks so the rules of hooks aren't violated by the early return.)
  if (!ACCOUNTS_ENABLED) {
    return null
  }
  return (
    <TopbarRightInner
      authenticatedUser={authenticatedUser}
      menuPlacement={menuPlacement}
    />
  )
}

const TopbarRightInner = ({
  authenticatedUser,
  menuPlacement,
}: {
  authenticatedUser?: schemas['UserRead']
  menuPlacement: 'below' | 'above'
}) => {
  const pathname = usePathname()
  const loginReturnTo = pathname ?? '/'
  const { isShown: isModalShown, hide: hideModal, show: showModal } = useModal()

  const onLoginClick = () => {
    showModal()
  }

  return authenticatedUser ? (
    <div>
      <div className="relative flex w-max shrink-0 flex-row items-center justify-between gap-x-6">
        <PublicProfileDropdown
          authenticatedUser={authenticatedUser}
          className="shrink-0"
          placement={menuPlacement}
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
