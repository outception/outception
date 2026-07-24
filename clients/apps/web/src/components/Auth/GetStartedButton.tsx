'use client'

import { usePostHog } from '@/hooks/posthog'
import KeyboardArrowRight from '@mui/icons-material/KeyboardArrowRight'
import { Button } from '@outception-com/orbit'
import { ComponentProps, FormEvent, useCallback, useState } from 'react'
import { twMerge } from 'tailwind-merge'
import { Modal } from '@outception-com/orbit'
import { useModal } from '../Modal/useModal'
import { AuthModal } from './AuthModal'

interface GetStartedButtonProps extends ComponentProps<typeof Button> {
  text?: string
}

const GetStartedButton = ({
  text: _text,
  wrapperClassNames,
  size = 'lg',
  ...props
}: GetStartedButtonProps) => {
  const posthog = usePostHog()
  const { isShown: isModalShown, hide: hideModal, show: showModal } = useModal()
  const [view, setView] = useState<'choose' | 'signup' | 'login'>('choose')
  const text = _text || 'Get Started'

  const onClick = useCallback(() => {
    posthog.capture('global:user:signup:click')
    setView('choose')
    showModal()
  }, [posthog, showModal])

  const onSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault()
      e.stopPropagation()
      onClick()
    },
    [onClick],
  )

  const handleGetStarted = () => {
    posthog.capture('dashboard:onboarding:mode:click', {
      mode: 'production',
      source: 'landing_modal',
    })
    setView('signup')
  }

  const modalTitles = {
    choose: 'Get started',
    signup: 'Get started',
    login: 'Sign in',
  } as const
  const modalTitle = modalTitles[view]

  const modalContents = {
    choose: (
      <GetStartedChoose
        onGetStarted={handleGetStarted}
        onLogin={() => setView('login')}
      />
    ),
    signup: <AuthModal returnTo="/dashboard" signup />,
    login: <AuthModal returnTo="/dashboard" />,
  }
  const modalContent = modalContents[view]

  return (
    <>
      <Button
        wrapperClassNames={twMerge(
          'flex flex-row items-center gap-x-2 ',
          wrapperClassNames,
        )}
        size={size}
        onClick={onClick}
        onSubmit={onSubmit}
        {...props}
      >
        <div>{text}</div>
        <KeyboardArrowRight
          className={size === 'lg' ? 'text-lg' : 'text-md'}
          fontSize="inherit"
        />
      </Button>

      <Modal
        title={modalTitle}
        isShown={isModalShown}
        hide={hideModal}
        modalContent={modalContent}
        className="lg:w-full lg:max-w-[480px]"
      />
    </>
  )
}

function GetStartedChoose({
  onGetStarted,
}: {
  onGetStarted: () => void
  onLogin: () => void
}) {
  return (
    <div className="flex flex-col gap-y-12 p-12">
      <div className="flex flex-col gap-y-1">
        <h1 className="text-xl font-medium">Welcome to Outception</h1>
        <p className="dark:text-outception-500 text-sm text-gray-500">
          A billing platform for the intelligence era.
        </p>
      </div>

      <div className="flex flex-col gap-y-4">
        <div>
          <Button fullWidth onClick={onGetStarted}>
            Get started
          </Button>
          <p className="dark:text-outception-500 mt-2 text-center text-xs text-gray-400">
            Create your organization and start accepting payments.
          </p>
        </div>
      </div>
    </div>
  )
}

export default GetStartedButton
