'use client'

import { useAuth } from '@/hooks'
import { useUpdateUser } from '@/hooks/queries'
import { useMonthDigitTypeahead } from '@/hooks/useMonthDigitTypeahead'
import { useT, useLocale } from '@/providers/locale'
import { schemas } from '@outception-com/client'
import { Button } from '@outception-com/orbit'
import { Input } from '@outception-com/orbit'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@outception-com/orbit'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@outception-com/ui/components/ui/form'
import { useCallback, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from '../Toast/use-toast'

interface FormSchema {
  firstName: string
  lastName: string
  country: string
  dobYear: string
  dobMonth: string
  dobDay: string
}

function parseDateOfBirth(dob: string | null | undefined) {
  if (!dob) return { year: '', month: '', day: '' }
  const parts = dob.split('-')
  return { year: parts[0] || '', month: parts[1] || '', day: parts[2] || '' }
}

function buildDateOfBirth(year: string, month: string, day: string) {
  if (year && month && day) {
    return `${year}-${month}-${day}`
  }
  return undefined
}

const PersonalInformationSettings = () => {
  const { currentUser, reloadUser } = useAuth()
  const updateUser = useUpdateUser()
  const t = useT()
  const locale = useLocale()

  const parsedDob = parseDateOfBirth(currentUser?.date_of_birth)

  const form = useForm<FormSchema>({
    defaultValues: {
      firstName: currentUser?.first_name || '',
      lastName: currentUser?.last_name || '',
      country: currentUser?.country || '',
      dobYear: parsedDob.year,
      dobMonth: parsedDob.month,
      dobDay: parsedDob.day,
    },
  })

  const { control, handleSubmit, reset } = form

  const handleMonthDigit = useMonthDigitTypeahead()

  useEffect(() => {
    if (currentUser) {
      const dob = parseDateOfBirth(currentUser.date_of_birth)
      reset({
        firstName: currentUser.first_name || '',
        lastName: currentUser.last_name || '',
        country: currentUser.country || '',
        dobYear: dob.year,
        dobMonth: dob.month,
        dobDay: dob.day,
      })
    }
  }, [currentUser, reset])

  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: 100 }, (_, i) =>
    String(currentYear - 18 - i),
  )
  const months = Array.from({ length: 12 }, (_, i) => ({
    value: String(i + 1).padStart(2, '0'),
    label: new Date(2000, i, 1).toLocaleString(locale, { month: 'long' }),
  }))
  const days = Array.from({ length: 31 }, (_, i) =>
    String(i + 1).padStart(2, '0'),
  )

  const onSubmit = useCallback(
    async (formData: FormSchema) => {
      const body: schemas['UserUpdate'] = {
        first_name: formData.firstName || undefined,
        last_name: formData.lastName || undefined,
        country: (formData.country || undefined) as
          | schemas['CountryAlpha2Input']
          | undefined,
        date_of_birth: buildDateOfBirth(
          formData.dobYear,
          formData.dobMonth,
          formData.dobDay,
        ),
      }

      const { error } = await updateUser.mutateAsync(body)

      if (error) {
        toast({
          title: t('account.personal.updateFailed'),
          description: t('account.personal.updateFailedDesc'),
        })
        return
      }

      await reloadUser()

      toast({
        title: t('account.personal.updated'),
        description: t('account.personal.updatedDesc'),
      })
    },
    [updateUser, reloadUser, t],
  )

  return (
    <Form {...form}>
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="dark:ring-outception-700 flex w-full flex-col gap-y-6 overflow-hidden rounded-2xl bg-transparent p-5 ring-1 ring-gray-200 dark:ring-1"
      >
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <FormField
            control={control}
            name="firstName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('account.personal.firstName')}</FormLabel>
                <FormControl>
                  <Input {...field} placeholder="Jane" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={control}
            name="lastName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('account.personal.lastName')}</FormLabel>
                <FormControl>
                  <Input {...field} placeholder="Doe" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="flex flex-col gap-y-2">
          <FormLabel>{t('account.personal.dob')}</FormLabel>
          <div className="grid grid-cols-3 gap-4">
            <FormField
              control={control}
              name="dobMonth"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger
                        onKeyDown={(e) => handleMonthDigit(e, field.onChange)}
                      >
                        <SelectValue
                          placeholder={t('account.personal.month')}
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {months.map((m) => (
                          <SelectItem key={m.value} value={m.value}>
                            {m.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name="dobDay"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('account.personal.day')} />
                      </SelectTrigger>
                      <SelectContent>
                        {days.map((d) => (
                          <SelectItem key={d} value={d}>
                            {d}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={control}
              name="dobYear"
              render={({ field }) => (
                <FormItem>
                  <FormControl>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger>
                        <SelectValue placeholder={t('account.personal.year')} />
                      </SelectTrigger>
                      <SelectContent>
                        {years.map((y) => (
                          <SelectItem key={y} value={y}>
                            {y}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button type="submit" disabled={updateUser.isPending}>
            {updateUser.isPending
              ? t('account.personal.saving')
              : t('account.personal.save')}
          </Button>
        </div>
      </form>
    </Form>
  )
}

export default PersonalInformationSettings
