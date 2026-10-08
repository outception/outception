import { useAuthSessionStart } from '@/hooks'
import { useToast } from '@/components/Toast/use-toast'
import Google from '@mui/icons-material/Google'
import { schemas } from '@outception-com/client'
import { Button, type ButtonProps } from '@outception-com/orbit/Button'
import { getGoogleAuthorizeLoginURL } from '@/utils/auth'
import { useT } from '@/providers/translate'

interface GoogleLoginButtonProps {
  authenticationSession: schemas['AuthenticationSession'] | null
  returnTo?: string
  signup?: boolean
  variant?: ButtonProps['variant']
}

const GoogleLoginButton = ({
  authenticationSession,
  returnTo,
  signup,
  variant,
}: GoogleLoginButtonProps) => {
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
    window.location.href = getGoogleAuthorizeLoginURL()
  }

  return (
    <a onClick={onClick}>
      <Button
        variant={variant}
        wrapperClassNames="space-x-2 p-2.5 px-5"
        fullWidth
      >
        <Google />
        <div className="w-32 text-left">
          {signup ? t('auth.googleSignup') : t('auth.google')}
        </div>
      </Button>
    </a>
  )
}

export default GoogleLoginButton
