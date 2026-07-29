import { useToast } from '@/components/Toast/use-toast'
import { useAuthSessionStart } from '@/hooks'
import { usePostHog, type EventName } from '@/hooks/posthog'
import { useT } from '@/providers/locale'
import { getMicrosoftAuthorizeLoginURL } from '@/utils/auth'
import Microsoft from '@mui/icons-material/Microsoft'
import { schemas } from '@outception-com/client'
import { Button, type ButtonProps } from '@outception-com/orbit'

interface MicrosoftLoginButtonProps {
  authenticationSession: schemas['AuthenticationSession'] | null
  returnTo?: string
  signup?: boolean
  variant?: ButtonProps['variant']
}

const MicrosoftLoginButton = ({
  authenticationSession,
  returnTo,
  signup,
  variant,
}: MicrosoftLoginButtonProps) => {
  const posthog = usePostHog()
  const authSessionStart = useAuthSessionStart()
  const { toast } = useToast()
  const t = useT()

  const onClick = async () => {
    let eventName: EventName = 'global:user:login:submit'
    if (signup) {
      eventName = 'global:user:signup:submit'
    }
    posthog.capture(eventName, {
      method: 'microsoft',
    })

    if (!authenticationSession) {
      try {
        await authSessionStart.mutateAsync(returnTo)
      } catch {
        toast({
          title: t('auth.failedTitle'),
          description: t('auth.failedBody'),
        })
        return
      }
    }
    window.location.href = getMicrosoftAuthorizeLoginURL()
  }

  return (
    <a onClick={onClick}>
      <Button
        variant={variant}
        wrapperClassNames="space-x-2 p-2.5 px-5"
        fullWidth
      >
        <Microsoft />
        <div className="w-32 text-left">
          {signup ? t('auth.microsoftSignup') : t('auth.microsoft')}
        </div>
      </Button>
    </a>
  )
}

export default MicrosoftLoginButton
