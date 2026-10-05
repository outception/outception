import { useAuthSessionStart } from '@/hooks'
import { useToast } from '@/components/Toast/use-toast'
import Apple from '@mui/icons-material/Apple'
import { schemas } from '@outception-com/client'
import { Button, type ButtonProps } from '@outception-com/orbit/Button'
import { getAppleAuthorizeURL } from '@/utils/auth'
import { useT } from '@/providers/translate'

interface AppleLoginButtonProps {
  authenticationSession: schemas['AuthenticationSession'] | null
  returnTo?: string
  signup?: boolean
  variant?: ButtonProps['variant']
}

const AppleLoginButton = ({
  authenticationSession,
  returnTo,
  signup,
  variant,
}: AppleLoginButtonProps) => {
  const authSessionStart = useAuthSessionStart()
  const { toast } = useToast()
  const t = useT()

  const onClick = async () => {
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
    window.location.href = getAppleAuthorizeURL()
  }

  return (
    <a onClick={onClick}>
      <Button
        variant={variant}
        wrapperClassNames="space-x-2 p-2.5 px-5"
        fullWidth
      >
        <Apple />
        <div className="w-32 text-left">
          {signup ? t('auth.appleSignup') : t('auth.apple')}
        </div>
      </Button>
    </a>
  )
}

export default AppleLoginButton
