'use client'

import { useBackupCodesVerify } from '@/hooks'
import { setValidationErrors } from '@/utils/api/errors'
import { isValidationError } from '@outception-com/client'
import { Button } from '@outception-com/orbit'
import { Input } from '@outception-com/orbit'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@outception-com/ui/components/ui/form'
import { useRouter } from 'next/navigation'
import { useRef, useState } from 'react'
import { SubmitHandler, useForm } from 'react-hook-form'

const VerifyPage = () => {
  const form = useForm<{ code: string }>()
  const { control, handleSubmit, setError } = form
  const backupCodesVerify = useBackupCodesVerify()
  const router = useRouter()

  const [loading, setLoading] = useState(false)
  // Synchronous guard: a fast double-click before `loading` re-renders would
  // otherwise fire two verifies and burn two single-use backup codes.
  const submittingRef = useRef(false)
  const onSubmit: SubmitHandler<{ code: string }> = async ({ code }) => {
    if (submittingRef.current) return
    submittingRef.current = true
    setLoading(true)
    try {
      const { error } = await backupCodesVerify.mutateAsync({ code })
      if (error) {
        if (isValidationError(error.detail)) {
          setValidationErrors(error.detail, setError)
        } else if (error.detail) {
          setError('code', { message: error.detail })
        }
        return
      }
      router.push('/auth')
    } catch {
      setError('code', {
        message: 'An unexpected error occurred. Please try again.',
      })
    } finally {
      setLoading(false)
      submittingRef.current = false
    }
  }

  return (
    <Form {...form}>
      <form
        className="flex w-full flex-col items-center gap-y-6"
        onSubmit={handleSubmit(onSubmit)}
      >
        <FormField
          control={control}
          name="code"
          render={({ field }) => {
            return (
              <FormItem className="w-full">
                <FormControl>
                  <Input
                    type="text"
                    placeholder="Backup code"
                    autoComplete="one-time-code"
                    className="text-center"
                    {...field}
                    autoFocus={true}
                  />
                </FormControl>
                <FormMessage className="text-center" />
              </FormItem>
            )
          }}
        />
        <Button type="submit" size="lg" className="w-full" loading={loading}>
          Sign in
        </Button>
      </form>
    </Form>
  )
}

export default VerifyPage
